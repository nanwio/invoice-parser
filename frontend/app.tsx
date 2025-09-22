// Copyright 2024 Artificial Intelligence Labs, SL

/**
 * Main React application - SIMPLE and MINIMAL
 * One responsibility: render the invoice upload page
 */

import React from 'react';
import { InvoiceUploadPage } from './pages/invoice_upload/main_page';
import './styles/app.css';

export function App() {
  return (
    <div className="app">
      <InvoiceUploadPage />
    </div>
  );
}

export default App;