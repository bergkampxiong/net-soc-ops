import React from 'react';
import { RouteObject } from 'react-router-dom';
import VisualDesigner from '../pages/rpa/VisualDesigner';

const routes: RouteObject[] = [
  {
    path: '/rpa/process-orchestration/visual-designer',
    element: <VisualDesigner />
  }
];

export default routes; 