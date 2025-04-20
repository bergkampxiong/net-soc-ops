import React from 'react';
import { RouteObject } from 'react-router-dom';
import { ProcessList } from '../pages/process-designer/list';
import { ProcessEdit } from '../pages/process-designer/edit';
import { ProcessView } from '../pages/process-designer/view';
import { ProcessExecute } from '../pages/process-designer/execute';

export const processDesignerRoutes: RouteObject[] = [
  {
    path: 'process-designer',
    children: [
      {
        index: true,
        element: <ProcessList />,
      },
      {
        path: 'edit/:id?',
        element: <ProcessEdit />,
      },
      {
        path: 'view/:id',
        element: <ProcessView />,
      },
      {
        path: 'execute/:id',
        element: <ProcessExecute />,
      },
    ],
  },
]; 