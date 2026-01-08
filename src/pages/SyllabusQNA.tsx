import React, { useState, type JSX } from 'react';
import { Upload, BookOpen, HelpCircle, FileText } from 'lucide-react';

interface CourseInfo {
  course_code: string;
  course_name: string;
  total_units: number;
}

interface UploadResponse {
  message: string;
  available_cos: string[];
  course_info: CourseInfo;
}

interface TopicsResponse {
  course_outcome: string;
  unit_id: string;
  unit_title: string;
  periods: number;
  topics: { [key: string]: string[] };
}

interface QuestionResponse {
  answer: string;
  course_outcome: string;
  unit: string;
  question: string;
  context_info: {
    unit_id: string;
    topics_covered: string[];
  };
}

const SyllabusQnA: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(null);
  const [selectedCO, setSelectedCO] = useState<string>('');
  const [topicsData, setTopicsData] = useState<TopicsResponse | null>(null);
  const [prompt, setPrompt] = useState<string>('');
  const [questionResponse, setQuestionResponse] = useState<QuestionResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'upload' | 'topics' | 'questions'>('upload');

  const API_BASE_URL = 'http://127.0.0.1:5000';

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a PDF file');
      return;
    }

    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/upload-pdf`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data: UploadResponse = await response.json();
      setUploadResponse(data);
      setActiveTab('topics');
    } catch (err) {
      setError('Failed to upload PDF. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGetTopics = async () => {
    if (!selectedCO) {
      setError('Please select a Course Outcome');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/get-co-topics/${selectedCO}`);

      if (!response.ok) {
        throw new Error('Failed to fetch topics');
      }

      const data: TopicsResponse = await response.json();
      setTopicsData(data);
    } catch (err) {
      setError('Failed to fetch topics. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleAskQuestion = async () => {
    if (!selectedCO || !prompt) {
      setError('Please select a Course Outcome and enter a prompt');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/ask-question`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          course_outcome: selectedCO,
          prompt: prompt,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate questions');
      }

      const data: QuestionResponse = await response.json();
      setQuestionResponse(data);
    } catch (err) {
      setError('Failed to generate questions. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const formatAnswer = (answer: string) => {
    const lines = answer.split('\n').filter(line => line.trim() !== '');
    
    return lines.map((line, index) => {
      
      
      const boldRegex = /\*\*(.*?)\*\*/g;
      const parts: JSX.Element[] = [];
      let lastIndex = 0;
      let match;

      while ((match = boldRegex.exec(line)) !== null) {
        if (match.index > lastIndex) {
          parts.push(<span key={`text-${index}-${lastIndex}`}>{line.slice(lastIndex, match.index)}</span>);
        }
        parts.push(<strong key={`bold-${index}-${match.index}`}>{match[1]}</strong>);
        lastIndex = match.index + match[0].length;
      }

      if (lastIndex < line.length) {
        parts.push(<span key={`text-${index}-${lastIndex}`}>{line.slice(lastIndex)}</span>);
      }

      const className = line.match(/^\d+\./) ? 'question-item' : 
                       line.match(/^\*\*.*QUESTIONS.*\*\*/) || line.match(/MARK QUESTIONS/) ? 'section-header' : '';

      return (
        <p key={index} className={className}>
          {parts.length > 0 ? parts : line}
        </p>
      );
    });
  };

  return (
    <div className="app-container">
      <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

    body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 0;
}

      .app-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 100vh;
  justify-content: flex-start; /* or center if you want vertical centering too */
}

        .header {
          text-align: center;
          color: white;
          margin-bottom: 2rem;
        }

        .header h1 {
          font-size: 2.5rem;
          font-weight: 700;
          margin-bottom: 0.5rem;
          text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        }

        .header p {
          font-size: 1.1rem;
          opacity: 0.9;
        }

        .tabs {
          display: flex;
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .tab-button {
          flex: 1;
          padding: 1rem;
          background: rgba(255, 255, 255, 0.2);
          border: 2px solid rgba(255, 255, 255, 0.3);
          color: white;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          border-radius: 12px;
          transition: all 0.3s ease;
          backdrop-filter: blur(10px);
        }

        .tab-button:hover {
          background: rgba(255, 255, 255, 0.3);
          transform: translateY(-2px);
        }

        .tab-button.active {
          background: white;
          color: #667eea;
          border-color: white;
        }

        .card {
          background: white;
          border-radius: 16px;
          padding: 2rem;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
          margin-bottom: 2rem;
        }

        .card h2 {
          color: #667eea;
          font-size: 1.8rem;
          margin-bottom: 1.5rem;
          padding-bottom: 0.5rem;
          border-bottom: 3px solid #667eea;
        }

        .file-upload-section {
          margin-bottom: 2rem;
        }

        .file-input-wrapper {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          margin-bottom: 1rem;
          padding: 3rem;
          border: 2px dashed #667eea;
          border-radius: 8px;
          background: #f8f9ff;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .file-input-wrapper:hover {
          border-color: #764ba2;
          background: #f0f2ff;
        }

        .file-input {
          position: absolute;
          opacity: 0;
          width: 100%;
          height: 100%;
          cursor: pointer;
        }

        .upload-placeholder {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1rem;
          color: #667eea;
          pointer-events: none;
        }

        .upload-icon {
          width: 48px;
          height: 48px;
        }

        .upload-text {
          font-weight: 600;
          font-size: 1.1rem;
        }

        .upload-subtext {
          font-size: 0.9rem;
          color: #999;
        }

        .button {
          padding: 1rem 2rem;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }

        .button:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }

        .button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }

        .course-info {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 1.5rem;
          border-radius: 12px;
          margin-bottom: 1.5rem;
        }

        .course-info h3 {
          font-size: 1.5rem;
          margin-bottom: 1rem;
        }

        .info-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }

        .info-item {
          background: rgba(255, 255, 255, 0.2);
          padding: 1rem;
          border-radius: 8px;
          backdrop-filter: blur(10px);
        }

        .info-label {
          font-size: 0.85rem;
          opacity: 0.9;
          margin-bottom: 0.25rem;
        }

        .info-value {
          font-size: 1.2rem;
          font-weight: 600;
        }

        .co-badges {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-top: 1rem;
        }

        .co-badge {
          background: rgba(255, 255, 255, 0.3);
          padding: 0.5rem 1rem;
          border-radius: 20px;
          font-weight: 600;
          font-size: 0.9rem;
        }

        .form-group {
          margin-bottom: 1.5rem;
        }

        .form-label {
          display: block;
          color: #333;
          font-weight: 600;
          margin-bottom: 0.5rem;
          font-size: 1rem;
        }

        .select {
          width: 100%;
          padding: 0.875rem;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          font-size: 1rem;
          background: white;
          cursor: pointer;
          transition: all 0.3s ease;
          color: black;
        }

        .select:focus {
          outline: none;
          border-color: #667eea;
          box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .textarea {
          width: 100%;
          padding: 1rem;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          font-size: 1rem;
          font-family: inherit;
          resize: vertical;
          min-height: 120px;
          transition: all 0.3s ease;
        }

        .textarea:focus {
          outline: none;
          border-color: #667eea;
          box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .topics-display {
          background: #f8f9ff;
          padding: 1.5rem;
          border-radius: 12px;
          color: black;
          border: 2px solid #e0e7ff;
        }

        .topics-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 1rem;
          border-radius: 8px;
          margin-bottom: 1rem;
        }

        .topics-header h3 {
          font-size: 1.3rem;
          margin-bottom: 0.5rem;
        }

        .topics-meta {
          font-size: 0.9rem;
          opacity: 0.9;
        }

        .topic-category {
          margin-bottom: 1.5rem;
        }

        .category-title {
          color: #667eea;
          font-weight: 600;
          font-size: 1.1rem;
          margin-bottom: 0.75rem;
          padding-bottom: 0.5rem;
          border-bottom: 2px solid #667eea;
        }

        .topic-list {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 0.5rem;
        }

        .topic-item {
          background: white;
          padding: 0.75rem;
          border-radius: 6px;
          border-left: 3px solid #667eea;
          font-size: 0.95rem;
          transition: all 0.2s ease;
        }

        .topic-item:hover {
          transform: translateX(5px);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .questions-display {
          background: #f8f9ff;
          padding: 2rem;
          border-radius: 12px;
          border: 2px solid #e0e7ff;
          line-height: 1.8;
        }

        .questions-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 1.5rem;
          border-radius: 8px;
          margin-bottom: 1.5rem;
        }

        .questions-header h3 {
          font-size: 1.5rem;
          margin-bottom: 0.5rem;
        }

        .section-header {
          color: #667eea;
          font-weight: 700;
          font-size: 1.2rem;
          margin-top: 2rem;
          margin-bottom: 1rem;
          padding: 0.5rem 0;
          border-bottom: 2px solid #667eea;
        }

        .section-header:first-child {
          margin-top: 0;
        }

        .question-item {
          background: white;
          padding: 1.25rem;
          margin-bottom: 1rem;
          border-radius: 8px;
          border-left: 4px solid #667eea;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
          transition: all 0.3s ease;
        }

        .question-item:hover {
          transform: translateX(5px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        .questions-display p {
          margin-bottom: 0.5rem;
          color: #333;
        }

        .questions-display strong {
          color: #667eea;
          font-weight: 700;
        }

        .error {
          background: #fee;
          color: #c33;
          padding: 1rem;
          border-radius: 8px;
          margin-bottom: 1rem;
          border-left: 4px solid #c33;
        }

        .loading {
          text-align: center;
          padding: 2rem;
          color: #667eea;
          font-weight: 600;
          font-size: 1.1rem;
        }

        .loading::after {
          content: '...';
          animation: dots 1.5s steps(4, end) infinite;
        }

        @keyframes dots {
          0%, 20% { content: '.'; }
          40% { content: '..'; }
          60%, 100% { content: '...'; }
        }

        .empty-state {
          text-align: center;
          padding: 3rem;
          color: #999;
        }

        .empty-state-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
        }
      `}</style>

      <div className="header">
        <h1><BookOpen size={40} style={{display: 'inline', marginRight: '1rem', verticalAlign: 'middle'}} />Syllabus Question Generator</h1>
        <p>Upload your syllabus PDF and generate questions based on Course Outcomes</p>
      </div>

      <div className="tabs">
        <button 
          className={`tab-button ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          <Upload size={20} style={{display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle'}} />
          Upload Syllabus
        </button>
        <button 
          className={`tab-button ${activeTab === 'topics' ? 'active' : ''}`}
          onClick={() => setActiveTab('topics')}
          disabled={!uploadResponse}
        >
          <FileText size={20} style={{display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle'}} />
          View Topics
        </button>
        <button 
          className={`tab-button ${activeTab === 'questions' ? 'active' : ''}`}
          onClick={() => setActiveTab('questions')}
          disabled={!uploadResponse}
        >
          <HelpCircle size={20} style={{display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle'}} />
          Generate Questions
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {activeTab === 'upload' && (
        <div className="card">
          <h2>Upload Syllabus PDF</h2>
          <div className="file-upload-section">
            <div className="file-input-wrapper">
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="file-input"
              />
              <div className="upload-placeholder">
                <Upload className="upload-icon" />
                <div className="upload-text">Click to upload or drag and drop</div>
                <div className="upload-subtext">PDF files only</div>
              </div>
            </div>
            {file && <p style={{textAlign: 'center', marginBottom: '1rem'}}>Selected: <strong>{file.name}</strong></p>}
            <button 
              onClick={handleUpload} 
              disabled={!file || loading}
              className="button"
            >
              {loading ? 'Uploading...' : 'Upload PDF'}
            </button>
          </div>

          {uploadResponse && (
            <div className="course-info">
              <h3>✓ {uploadResponse.message}</h3>
              <div className="info-grid">
                <div className="info-item">
                  <div className="info-label">Course Code</div>
                  <div className="info-value">{uploadResponse.course_info.course_code}</div>
                </div>
                <div className="info-item">
                  <div className="info-label">Course Name</div>
                  <div className="info-value">{uploadResponse.course_info.course_name}</div>
                </div>
                <div className="info-item">
                  <div className="info-label">Total Units</div>
                  <div className="info-value">{uploadResponse.course_info.total_units}</div>
                </div>
              </div>
              <div>
                <div className="info-label">Available Course Outcomes:</div>
                <div className="co-badges">
                  {uploadResponse.available_cos.map(co => (
                    <span key={co} className="co-badge">{co}</span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'topics' && uploadResponse && (
        <div className="card">
          <h2>View Course Outcome Topics</h2>
          <div className="form-group">
            <label className="form-label">Select Course Outcome</label>
            <select 
              className="select"
              value={selectedCO}
              onChange={(e) => setSelectedCO(e.target.value)}
            >
              <option value="">-- Select CO --</option>
              {uploadResponse.available_cos.map(co => (
                <option key={co} value={co}>{co}</option>
              ))}
            </select>
          </div>
          <button 
            onClick={handleGetTopics}
            disabled={!selectedCO || loading}
            className="button"
          >
            {loading ? 'Loading...' : 'Get Topics'}
          </button>

          {topicsData && (
            <div className="topics-display">
              <div className="topics-header">
                <h3>{topicsData.course_outcome} - {topicsData.unit_title}</h3>
                <div className="topics-meta">
                  {topicsData.unit_id} | {topicsData.periods} Periods
                </div>
              </div>
              {Object.entries(topicsData.topics).map(([category, items]) => (
                <div key={category} className="topic-category">
                  <div className="category-title">{category}</div>
                  <div className="topic-list">
                    {items.map((item, idx) => (
                      <div key={idx} className="topic-item">• {item}</div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'questions' && uploadResponse && (
        <div className="card">
          <h2>Generate Questions</h2>
          <div className="form-group">
            <label className="form-label">Select Course Outcome</label>
            <select 
              className="select"
              value={selectedCO}
              onChange={(e) => setSelectedCO(e.target.value)}
            >
              <option value="">-- Select CO --</option>
              {uploadResponse.available_cos.map(co => (
                <option key={co} value={co}>{co}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Enter Your Prompt</label>
            <textarea
              className="textarea"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="E.g., I want ten 5 marks questions"
            />
          </div>

          <button 
            onClick={handleAskQuestion}
            disabled={!selectedCO || !prompt || loading}
            className="button"
          >
            {loading ? 'Generating...' : 'Generate Questions'}
          </button>

          {loading && <div className="loading">Generating questions</div>}

          {questionResponse && !loading && (
            <div className="questions-display">
              <div className="questions-header">
                <h3>{questionResponse.course_outcome} - {questionResponse.unit}</h3>
                <div>Unit: {questionResponse.context_info.unit_id}</div>
                <div>Topics Covered: {questionResponse.context_info.topics_covered.join(', ')}</div>
              </div>
              <div>
                {formatAnswer(questionResponse.answer)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SyllabusQnA;