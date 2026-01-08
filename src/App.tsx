import React from 'react';
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import SyllabusQnA from './pages/SyllabusQNA';


const App: React.FC = () => {
  return (
    <Router>
      <div className="app">
        <Routes>
          <Route path="/" element={<SyllabusQnA />} />
        </Routes>
       
        
   
      </div>
    </Router>
  );
};

export default App;