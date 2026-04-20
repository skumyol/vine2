import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from '@/components/layout'
import { Dashboard } from '@/pages/dashboard'
import { ArchitecturePage } from '@/pages/architecture'

function App() {
  // Detect if running under /vine2/ path (production) or root (local dev)
  const basename = window.location.pathname.startsWith('/vine2') ? '/vine2' : '/'

  return (
    <BrowserRouter basename={basename}>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/architecture" element={<ArchitecturePage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
