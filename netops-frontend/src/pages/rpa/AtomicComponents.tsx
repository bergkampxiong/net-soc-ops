import React from 'react';
import { Outlet } from 'react-router-dom';
import styles from './AtomicComponents.module.less';

const AtomicComponents: React.FC = () => {
  return (
    <div className={styles.container}>
      <Outlet />
    </div>
  );
};

export default AtomicComponents; 