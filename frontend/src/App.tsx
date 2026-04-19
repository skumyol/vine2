import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from '@/components/layout'
import { Dashboard } from '@/pages/dashboard'
import { ArchitecturePage } from '@/pages/architecture'

function App() {
  return (
    <BrowserRouter>
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
