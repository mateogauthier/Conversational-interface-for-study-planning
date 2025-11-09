# Study Planning Assistant - Frontend

A modern React frontend for the Study Planning API with RAG capabilities.

## Features

- **Document Upload**: Drag-and-drop interface for uploading study materials
- **Intelligent Query**: Chat-like interface for querying documents with RAG
- **File Management**: View and manage uploaded documents
- **Real-time Stats**: Dashboard showing system statistics
- **Responsive Design**: Works on desktop and mobile devices
- **Modern UI**: Clean, professional interface with smooth animations

## Technology Stack

- **React 18**: Modern React with hooks
- **Vite**: Fast build tool and dev server
- **React Router**: Client-side routing
- **Axios**: HTTP client for API calls
- **Lucide React**: Beautiful icon library
- **CSS3**: Custom styling with responsive design

## Development

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Access at http://localhost:3000
```

### Environment Variables

Create `.env.development` for development:
```
VITE_API_URL=http://localhost:8000
```

Create `.env.production` for production:
```
VITE_API_URL=/api
```

### Available Scripts

- `npm run dev` - Start development server with hot-reload
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint

## Docker Deployment

The frontend is containerized with nginx and included in the main docker-compose setup:

```bash
# Build and run all services (from project root)
docker compose up --build

# Access frontend at http://localhost:3000
# Backend API at http://localhost:8000
```

In production, nginx proxies `/api/*` requests to the backend FastAPI service.

## Project Structure

```
FRONTEND/
├── src/
│   ├── pages/           # Page components
│   │   ├── HomePage.jsx
│   │   ├── UploadPage.jsx
│   │   ├── QueryPage.jsx
│   │   └── FilesPage.jsx
│   ├── services/        # API client
│   │   └── api.js
│   ├── App.jsx          # Main app with routing
│   ├── App.css          # Global styles
│   └── main.jsx         # Entry point
├── public/              # Static assets
├── nginx.conf           # Nginx configuration
├── Dockerfile           # Multi-stage Docker build
└── vite.config.js       # Vite configuration
```

## API Integration

The frontend consumes all backend API endpoints:

### File Management
- `POST /files/upload` - Upload documents
- `GET /files/` - List all files
- `GET /files/{filename}` - Get file details
- `DELETE /files/{filename}` - Delete file
- `GET /files/supported/extensions` - Get supported file types

### RAG Operations
- `POST /rag/query` - Query documents with LLM
- `POST /rag/search` - Search documents
- `GET /rag/stats` - Get RAG statistics
- `POST /rag/reset` - Reset RAG collection
- `GET /rag/health` - RAG health check

### LLM Operations
- `POST /llm/query` - Direct LLM query
- `GET /llm/status` - Get LLM status
- `GET /llm/models` - List available models
- `GET /llm/health` - LLM health check

## Features by Page

### Home Page
- System statistics dashboard
- Quick action buttons
- System information display
- Feature explanations

### Upload Page
- Drag-and-drop file upload
- Upload progress indicator
- File type validation
- Supported formats display

### Query Page
- Chat-like interface
- Configurable chunk retrieval
- Language selection
- Source attribution
- Message history

### Files Page
- File listing with metadata
- Delete functionality
- File size and date display
- Support status indicators

## Development Notes

- The dev server runs on port 3000 with hot module replacement
- API calls are proxied to avoid CORS issues in development
- Production build uses nginx for optimal performance
- All API calls have proper error handling
- Loading states are shown for better UX

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## License

Part of the Study Planning Assistant project.
