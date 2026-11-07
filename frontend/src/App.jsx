import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import ProtectedRoute, { GuestRoute } from './components/ProtectedRoute'
import ChatPage from './pages/ChatPage'
import DocumentsPage from './pages/DocumentsPage'
import HistoryPage from './pages/HistoryPage'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'

const router = createBrowserRouter([
  {
    element: <GuestRoute />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/signup', element: <SignupPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: '/chat', element: <ChatPage /> },
          { path: '/documents', element: <DocumentsPage /> },
          { path: '/history', element: <HistoryPage /> },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/chat" replace /> },
])

export default function App() {
  return <RouterProvider router={router} />
}
