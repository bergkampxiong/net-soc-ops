import React from 'react';
import { Outlet } from 'react-router-dom';

const SystemIntegration: React.FC = () => {
  return (
    <div className="system-integration">
      <Outlet />
    </div>
  );
};

export default SystemIntegration; 