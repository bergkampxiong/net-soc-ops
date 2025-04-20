import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './styles/index.css';
import './styles/global.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

// 删除之前添加的未来标志
// import { UNSAFE_enhanceManualRouteObjects } from 'react-router-dom';
// UNSAFE_enhanceManualRouteObjects.v7_startTransition = true;
// UNSAFE_enhanceManualRouteObjects.v7_relativeSplatPath = true;

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true
      }}
    >
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

// 如果你想开始测量应用的性能，请传递一个函数
// 来记录结果（例如：reportWebVitals(console.log)）
// 或发送到分析端点。了解更多：https://bit.ly/CRA-vitals
reportWebVitals(); 