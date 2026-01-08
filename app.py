import os
import re
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from pypdf import PdfReader
from flask_cors import CORS  
app = Flask(__name__)
load_dotenv()

CORS(app)  

syllabus_data = None
CO_TO_UNIT_MAP = {}

def extract_text_from_pdf(file):
    reader = PdfReader(file)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)

def parse_course_metadata(text):

    metadata = {}
    
    course_name_match = re.search(r"Course Name\s+(.*?)\s+(?=\d|$)", text, re.I | re.S)
    if course_name_match:
        metadata["course_name"] = course_name_match.group(1).strip()
    
    course_code_match = re.search(r"Course Code\s+(\S+)", text)
    if course_code_match:
        metadata["course_code"] = course_code_match.group(1)
    
    semester_match = re.search(r"Semester\s+([IVX\d]+)", text)
    if semester_match:
        metadata["semester"] = semester_match.group(1)
    
    dept_match = re.search(r"Department\s+(.*?)\s+(?=Programme:|Course Code:|$)", text, re.I | re.S)
    if dept_match:
        metadata["department"] = dept_match.group(1).strip()
    
    programme_match = re.search(r"Programme[:\s]+(.*?)\s+(?=Semester|Course Code:|$)", text, re.I | re.S)
    if programme_match:
        metadata["programme"] = programme_match.group(1).strip()
    
    periods_match = re.search(r"Periods/Week\s+L\s+T\s+P\s+C\s+.*?\n\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", text)
    if periods_match:
        metadata["periods"] = {
            "lecture": int(periods_match.group(1)),
            "tutorial": int(periods_match.group(2)),
            "practical": int(periods_match.group(3)),
            "credits": int(periods_match.group(4))
        }
    
    marks_match = re.search(r"Maximum Marks.*?\n.*?\n.*?\s+(\d+)\s+(\d+)\s+(\d+)", text, re.S)
    if marks_match:
        metadata["marks_distribution"] = {
            "continuous_assessment": int(marks_match.group(1)),
            "end_semester_exam": int(marks_match.group(2)),
            "total_marks": int(marks_match.group(3))
        }
    
    prereq_match = re.search(r"Prerequisite\s+(.*?)\s+(?=Course Outcomes|On completion)", text, re.I | re.S)
    if prereq_match:
        metadata["prerequisite"] = prereq_match.group(1).strip()
    
    co_pattern = re.compile(r"(CO\d+)\s+(.*?)\s+(K\d+)", re.S)
    course_outcomes = []
    
    co_section_start = text.find("Course Outcomes")
    if co_section_start != -1:
        co_section = text[co_section_start:]
        co_end = co_section.find("UNIT")
        if co_end != -1:
            co_section = co_section[:co_end]
        
        for match in co_pattern.finditer(co_section):
            course_outcomes.append({
                "code": match.group(1),
                "description": match.group(2).strip(),
                "blooms_level": match.group(3)
            })
    
    metadata["course_outcomes"] = course_outcomes
    
    return metadata

def parse_units(text):
    unit_pattern = re.compile(
        r"(UNIT\s*[-–\s]*[IVX\d]+)\s+(.*?)\s+Periods\s*[:–]\s*(\d+)(.*?)(?=UNIT\s*[-–\s]*[IVX\d]+|COs/POs/PSOs Mapping|Text Books|Reference Books|Web References|Lecture Periods|\Z)",
        re.S | re.I
    )
    
    units = []
    
    for match in unit_pattern.finditer(text):
        unit_id = match.group(1).strip()
        title = match.group(2).strip()
        periods = int(match.group(3))
        content = match.group(4).strip()
        
        content = re.sub(r'Lecture Periods.*?Total Periods:\d+', '', content, flags=re.S | re.I)
        
        topics = {}
        
        blocks = re.split(r'\n(?=[A-Z][^a-z]*:)', content)
        
        for block in blocks:
            block = block.strip()
            if ':' in block:
                parts = block.split(':', 1)
                if len(parts) == 2:
                    heading = parts[0].strip()
                    content_text = parts[1].strip()
                    
                    content_text = re.sub(r'\bCO\d+\b', '', content_text).strip()
                    
                    topic_list = []
                    for topic in re.split(r'[–—\-•\n.]+', content_text):
                        topic = topic.strip()
                        if topic and len(topic) > 1:
                            topic = re.sub(r'[,.:;]+$', '', topic)
                            if topic:
                                topic_list.append(topic)
                    
                    if topic_list:
                        topics[heading] = topic_list
        
        co_match = re.search(r'\b(CO\d+)\b', content)
        co = co_match.group(1) if co_match else None
        
        units.append({
            "unit_id": unit_id,
            "title": title,
            "periods": periods,
            "topics": topics,
            "course_outcome": co
        })
    
    return units

def parse_total_periods(text):

    periods_info = {}
    
    lecture_match = re.search(r'Lecture Periods\s*[:–]\s*(\d+)', text, re.I)
    tutorial_match = re.search(r'Tutorial Periods\s*[:–]\s*(\d+|[-–])', text, re.I)
    practical_match = re.search(r'Practical Periods\s*[:–]\s*(\d+|[-–])', text, re.I)
    total_match = re.search(r'Total Periods\s*[:–]\s*(\d+)', text, re.I)
    
    if lecture_match:
        periods_info["lecture_periods"] = int(lecture_match.group(1))
    
    if tutorial_match:
        try:
            periods_info["tutorial_periods"] = int(tutorial_match.group(1))
        except ValueError:
            periods_info["tutorial_periods"] = 0
    
    if practical_match:
        try:
            periods_info["practical_periods"] = int(practical_match.group(1))
        except ValueError:
            periods_info["practical_periods"] = 0
    
    if total_match:
        periods_info["total_periods"] = int(total_match.group(1))
    
    return periods_info if periods_info else None

def parse_references(text):
    references = {
        "text_books": [],
        "reference_books": [],
        "web_references": []
    }
    
    tb_start = text.find("Text Books")
    rb_start = text.find("Reference Books")
    wr_start = text.find("Web References")
    
    if tb_start != -1:
        tb_end = rb_start if rb_start != -1 else wr_start if wr_start != -1 else len(text)
        tb_section = text[tb_start:tb_end]
        
        tb_items = re.findall(r'\d+\.\s+(.*?)(?=\d+\.|$)', tb_section, re.S)
        for item in tb_items:
            if item.strip():
                item = re.sub(r'\s*\n\s*', ' ', item.strip())
                references["text_books"].append(item)
    
    if rb_start != -1:
        rb_end = wr_start if wr_start != -1 else len(text)
        rb_section = text[rb_start:rb_end]
        
        rb_items = re.findall(r'\d+\.\s+(.*?)(?=\d+\.|$)', rb_section, re.S)
        for item in rb_items:
            if item.strip():
                item = re.sub(r'\s*\n\s*', ' ', item.strip())
                references["reference_books"].append(item)
    
    if wr_start != -1:
        wr_section = text[wr_start:]
        
        urls = re.findall(r'https?://[^\s]+', wr_section)
        for url in urls:
            references["web_references"].append(url.strip())
        
        wr_items = re.findall(r'\d+\.\s+(.*?)(?=\d+\.|$)', wr_section, re.S)
        for item in wr_items:
            item = item.strip()
            if item and item not in references["web_references"] and not item.startswith("http"):
                item = re.sub(r'\s*\n\s*', ' ', item)
                references["web_references"].append(item)
    
    return references

def parse_co_po_pso_table(text):

    table_start = text.find("COs/POs/PSOs Mapping")
    if table_start == -1:
        return None
    
    table_section = text[table_start:]
    
    next_section = re.search(r'\n\s*\n\s*[A-Z]', table_section)
    if next_section:
        table_section = table_section[:next_section.start()]
    
    rows = []
    lines = table_section.split('\n')
    
    for line in lines:
        line = line.strip()
        if re.match(r'^\d\s+', line):
            parts = line.split()
            if len(parts) >= 1:
                co_num = parts[0]
                mapping_values = []
                for val in parts[1:]:
                    if val == '-':
                        mapping_values.append(None)
                    elif val.isdigit():
                        mapping_values.append(int(val))
                    else:
                        mapping_values.append(None)
                
                po_mapping = {}
                pso_mapping = {}
                
                for i in range(12):
                    po_key = f"PO{i+1}"
                    po_value = mapping_values[i] if i < len(mapping_values) else None
                    po_mapping[po_key] = po_value
                
                for i in range(3):
                    pso_key = f"PSO{i+1}"
                    pso_index = 12 + i
                    pso_value = mapping_values[pso_index] if pso_index < len(mapping_values) else None
                    pso_mapping[pso_key] = pso_value
                
                rows.append({
                    "CO": f"CO{co_num}",
                    "POs": po_mapping,
                    "PSOs": pso_mapping
                })
    
    if not rows:
        return None
    
    return {
        "correlation_scale": {
            "1": "Low",
            "2": "Medium",
            "3": "High"
        },
        "mapping": rows
    }

def parse_assessment_details(text):

    assessment = {}
    
    assessment_section_start = text.find("Correlation Level")
    if assessment_section_start == -1:
        return None
    
    assessment_section = text[assessment_section_start:]
    
    assessment_match = re.search(
        r'Assessment\s*\n.*?\n.*?\n(.*?)\n.*?\n(.*?)(?=\n\s*\n|\Z)',
        assessment_section,
        re.S
    )
    
    if assessment_match:
        headers = re.findall(r'\b\w+\b', assessment_match.group(1))
        values = re.findall(r'\b\d+\b', assessment_match.group(2))
        
        if headers and values:
            components = []
            for i, header in enumerate(headers):
                if i < len(values):
                    components.append({
                        "component": header,
                        "marks": int(values[i])
                    })
            
            if components:
                assessment["components"] = components
                
                total_match = re.search(r'Total Marks\s+(\d+)', assessment_match.group(2))
                if total_match:
                    assessment["total_marks"] = int(total_match.group(1))
    
    return assessment if assessment else None



def build_co_to_unit_map(syllabus_data):

    co_map = {}
    
    if not syllabus_data or "syllabus_structure" not in syllabus_data:
        return co_map
    
    units = syllabus_data["syllabus_structure"].get("units", [])
    
    for unit in units:
        co_code = unit.get("course_outcome")
        if co_code:
            
            topics = unit.get("topics", {})
    
            topic_text = ""
            for category, subtopics in topics.items():
                topic_text += f"{category}:\n"
                for subtopic in subtopics:
                    topic_text += f"  - {subtopic}\n"
            
            if topic_text:
     
                co_map[co_code] = {
                    "unit_title": unit.get("title", ""),
                    "unit_id": unit.get("unit_id", ""),
                    "topics": topic_text,
                    "full_unit": unit
                }
    
    return co_map
def get_context_for_co(co_code):

    if not syllabus_data:
        return None
    

    if co_code in CO_TO_UNIT_MAP:
        context = CO_TO_UNIT_MAP[co_code]["topics"]
       
        bloom_level = "Remember" 
        
        if syllabus_data.get("course_metadata", {}).get("course_outcomes"):
            for co in syllabus_data["course_metadata"]["course_outcomes"]:
                if co["code"] == co_code:
                    
                    bloom_code = co.get("blooms_level", "K1")
                    bloom_mapping = {
                        "K1": "Remember",
                        "K2": "Understand", 
                        "K3": "Apply",
                        "K4": "Analyze",
                        "K5": "Evaluate",
                        "K6": "Create"
                    }
                    bloom_level = bloom_mapping.get(bloom_code, "Remember")
                    break
        
        return {
            "topics": context,
            "bloom_level": bloom_level
        }
    
    return None

def query_huggingface(prompt, context=None):

    API_URL = "https://router.huggingface.co/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {os.getenv('HF_TOKEN')}",
        "Content-Type": "application/json"
    }
  
    if context:
        system_message = f"You are a course instructor. Here are the course topics:\n\n{context}\n\n"
        system_message += "CRITICAL: When generating questions, you MUST:\n"
        system_message += "1. Provide ONLY QUESTIONS, no answers\n"
        system_message += "2. Use DIFFERENT Bloom's taxonomy levels for different questions\n"
        system_message += "3. Match Bloom's level to question complexity:\n"
        system_message += "   - Simple recall → Remember\n"
        system_message += "   - Explanation → Understand\n"
        system_message += "   - Application → Apply\n"
        system_message += "   - Analysis → Analyze\n"
        system_message += "   - Evaluation → Evaluate\n"
        system_message += "   - Creation → Create\n"
        system_message += "4. Vary Bloom's levels naturally across questions\n"
        system_message += "5. Include Bloom's level in brackets after each question\n"
        system_message += "6. No multiple choice questions\n"
    else:
        system_message = "You are a course instructor."
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json={
                "model": "meta-llama/Llama-3.1-8B-Instruct:novita",
                "messages": messages,
                "max_tokens": 2000,
                "temperature": 0.8
            }
        )
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            return "Error: No response from AI model."
            
    except requests.exceptions.RequestException as e:
        return f"Error connecting to AI service: {str(e)}"
    except Exception as e:
        return f"Error processing AI response: {str(e)}"

@app.route("/upload-pdf", methods=["POST"])
def upload_pdf():
    """Upload and parse syllabus PDF"""
    global syllabus_data, CO_TO_UNIT_MAP
    
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if not file.filename.endswith(".pdf"):
        return jsonify({"error": "Only PDF files allowed"}), 400

    try:
        text = extract_text_from_pdf(file)
        
 
        course_metadata = parse_course_metadata(text)
        units = parse_units(text)
        total_periods_info = parse_total_periods(text)
        references = parse_references(text)
        co_po_pso = parse_co_po_pso_table(text)
        assessment = parse_assessment_details(text)
        
        syllabus_data = {
            "course_metadata": course_metadata,
            "syllabus_structure": {
                "total_units": len(units),
                "unit_periods": units[0]["periods"] if units else None,
                "units": units,
                "total_periods_info": total_periods_info
            },
            "assessment_details": assessment,
            "references": references,
            "co_po_pso_mapping": co_po_pso
        }
        
  
        CO_TO_UNIT_MAP = build_co_to_unit_map(syllabus_data)
        

        available_cos = list(CO_TO_UNIT_MAP.keys())
        
        response = {
            "message": "Syllabus uploaded successfully",
            "available_cos": available_cos,
            "course_info": {
                "course_code": syllabus_data["course_metadata"].get("course_code"),
                "course_name": syllabus_data["course_metadata"].get("course_name"),
                "total_units": len(units)
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": f"Error processing PDF: {str(e)}"}), 500

@app.route("/ask-question", methods=["POST"])
def ask_question():
   
    global syllabus_data, CO_TO_UNIT_MAP
    
 
    if not syllabus_data:
        return jsonify({"error": "No syllabus loaded. Please upload a PDF first."}), 400
  
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    co_code = data.get("course_outcome")
    prompt = data.get("prompt")
    
    if not co_code:
        return jsonify({"error": "course_outcome is required"}), 400
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    
 
    if not re.match(r'^CO\d+$', co_code, re.IGNORECASE):
        return jsonify({"error": "Invalid CO format. Use format like 'CO1', 'CO2', etc."}), 400
    
    co_code = co_code.upper()
    
    if co_code not in CO_TO_UNIT_MAP:
        available_cos = list(CO_TO_UNIT_MAP.keys())
        return jsonify({
            "error": f"CO '{co_code}' not found in syllabus.",
            "available_cos": available_cos
        }), 404
    
    context_data = get_context_for_co(co_code)
    context = context_data["topics"] if context_data else ""
    
    unit_topics = CO_TO_UNIT_MAP[co_code]['full_unit'].get('topics', {})
    
    enhanced_prompt = f"""
    User Request: {prompt}
    
    IMPORTANT INSTRUCTIONS:
    1. Generate ONLY QUESTIONS, NO ANSWERS
    2. Do NOT include any answers, solutions, or explanations
    3. Questions should be appropriate for the marks requested:
       - 2 mark questions: Simple, direct questions (Use: Remember, Understand)
       - 5 mark questions: Questions requiring brief explanations (Use: Apply, Analyze)
       - 10 mark questions: Questions requiring detailed explanations or comparisons (Use: Evaluate, Create)
    4. Format: Clear numbered questions grouped by marks
    5. DO NOT create multiple choice questions (MCQs)
    6. DISTRIBUTE questions proportionally across ALL topics in the course material
    7. Ensure comprehensive coverage of ALL subtopics
    8. For EACH question, include APPROPRIATE Bloom's taxonomy level in brackets at the end
    9. USE DIFFERENT BLOOM'S LEVELS based on question complexity:
       - Remember: Recall facts, definitions (Simple recall questions)
       - Understand: Explain ideas, compare, summarize (Explanation questions)
       - Apply: Use information in new situations (Application questions)
       - Analyze: Break down concepts, identify relationships (Analysis questions)
       - Evaluate: Make judgments, critique, justify (Evaluation questions)
       - Create: Design, construct, develop new ideas (Creation questions)
    10. DO NOT use the same Bloom's level for all questions
    11. Vary the Bloom's levels appropriately
    12. Match Bloom's level to question difficulty
    13. Number questions clearly
    14. Group by mark value
    
    FORMAT:
    2-MARK QUESTIONS:
    1. Question text? [Bloom's Level]
    2. Another question? [Different Bloom's Level]
    
    5-MARK QUESTIONS:
    1. Question requiring explanation? [Bloom's Level]
    
    10-MARK QUESTIONS:
    1. Detailed descriptive question? [Bloom's Level]
    
    Now generate the requested questions: "{prompt}"
    """
    
    
    answer = query_huggingface(enhanced_prompt, context)
    
   
    response = {
        "course_outcome": co_code,
        "unit": CO_TO_UNIT_MAP[co_code]['unit_title'],
        "question": prompt,
        "answer": answer,
        "context_info": {
            "unit_id": CO_TO_UNIT_MAP[co_code]['unit_id'],
            "topics_covered": list(unit_topics.keys())
        }
    }
    
    return jsonify(response)

@app.route("/get-syllabus-info", methods=["GET"])
def get_syllabus_info():
    global syllabus_data, CO_TO_UNIT_MAP
    
    if not syllabus_data:
        return jsonify({"message": "No syllabus loaded"}), 404
    
    course_info = syllabus_data.get("course_metadata", {})
    
    response = {
        "course_code": course_info.get("course_code"),
        "course_name": course_info.get("course_name"),
        "department": course_info.get("department"),
        "semester": course_info.get("semester"),
        "total_units": syllabus_data.get("syllabus_structure", {}).get("total_units", 0),
        "available_cos": list(CO_TO_UNIT_MAP.keys()),
        "units": []
    }
    units = syllabus_data.get("syllabus_structure", {}).get("units", [])
    for unit in units:
        response["units"].append({
            "unit_id": unit.get("unit_id"),
            "title": unit.get("title"),
            "course_outcome": unit.get("course_outcome"),
            "periods": unit.get("periods")
        })
    
    return jsonify(response)

@app.route("/get-co-topics/<co_code>", methods=["GET"])
def get_co_topics(co_code):
   
    global CO_TO_UNIT_MAP
    
    if not syllabus_data:
        return jsonify({"error": "No syllabus loaded"}), 404
    
    co_code = co_code.upper()
    
    if co_code not in CO_TO_UNIT_MAP:
        available_cos = list(CO_TO_UNIT_MAP.keys())
        return jsonify({
            "error": f"CO '{co_code}' not found.",
            "available_cos": available_cos
        }), 404
    
    co_info = CO_TO_UNIT_MAP[co_code]
    
    return jsonify({
        "course_outcome": co_code,
        "unit_id": co_info["unit_id"],
        "unit_title": co_info["unit_title"],
        "topics": co_info["full_unit"].get("topics", {}),
        "periods": co_info["full_unit"].get("periods")
    })

if __name__ == "__main__":
   
    if not os.getenv("HF_TOKEN"):
        print("Warning: HF_TOKEN not found in environment variables.")
        print("Please set HF_TOKEN in your .env file or environment.")
    
    app.run(debug=True, port=5000)
