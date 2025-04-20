import React from 'react';
import { Outlet } from 'react-router-dom';
import styles from './ProcessOrchestration.module.less';

const ProcessOrchestration: React.FC = () => {
  return (
    <div className={styles.container}>
      <Outlet />
    </div>
  );
};

export default ProcessOrchestration; 