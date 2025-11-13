import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      // Header
      appTitle: 'Study Planning Assistant',

      // Navigation
      nav: {
        home: 'Home',
        files: 'Files',
        settings: 'Settings'
      },

      // Authentication
      auth: {
        welcome: 'Welcome to Study Planning Assistant',
        subtitle: 'Your intelligent companion for study materials and planning',
        features: 'Features',
        feature1: 'Upload and organize your study documents',
        feature2: 'Ask questions powered by AI',
        feature3: 'Get personalized learning assistance',
        loginButton: 'Sign In with Auth0',
        securedBy: 'Secured by',
        loading: 'Loading...',
        checking: 'Checking authentication...',
        logout: 'Logout'
      },

      // Home Page
      home: {
        title: 'Ask Questions About Your Documents',
        noMessages: 'No messages yet. Ask a question about your documents!',
        configureSettings: 'Configure your preferences in the Settings tab',
        placeholder: 'Ask a question about your documents...',
        send: 'Send',
        clearChat: 'Clear Chat',
        thinking: 'Thinking...',
        sources: 'Sources',
        model: 'Model',
        useRAG: 'Use RAG (Retrieval-Augmented Generation)',
        ragEnabled: 'Queries will use document context',
        ragDisabled: 'Direct LLM queries without documents'
      },

      // Files Page
      files: {
        uploadTitle: 'Upload Study Materials',
        manageTitle: 'Manage Files',
        uploadHint: 'Click or drag file to upload',
        uploadHintSelected: 'Size',
        supportedFormats: 'Supports PDF, Word, Excel, Text, and Markdown files',
        uploadButton: 'Upload File',
        cancel: 'Cancel',
        uploading: 'Uploading...',
        refresh: 'Refresh',
        delete: 'Delete',
        deleting: 'Deleting...',
        noFiles: 'No files uploaded yet',
        noFilesHint: 'Upload some documents to get started',
        totalFiles: 'Total files',
        uploaded: 'Uploaded',
        maxFileSize: 'Maximum file size',
        unsupported: 'File type not supported for RAG processing',
        uploadSuccess: 'File uploaded and processed successfully!',
        uploadSuccessNoRag: 'File uploaded but could not be processed for RAG.',
        uploadError: 'Upload failed. Please try again.',
        deleteConfirm: 'Are you sure you want to delete',
        deleteSuccess: 'deleted successfully.',
        deleteError: 'Failed to delete'
      },

      // Settings Page
      settings: {
        title: 'System Settings',
        userPreferences: 'User Preferences',
        defaultLanguage: 'Language',
        languageHint: 'Language for the interface and LLM responses.',
        preferredModel: 'Preferred LLM Model',
        preferredModelHint: 'Click on a model below to select it.',
        useRAG: 'Use RAG (Retrieval-Augmented Generation)',
        useRAGHint: 'When enabled, queries will search your documents and use their content as context for answers.',
        ragSaved: 'RAG preference saved!',
        contextChunks: 'Number of Context Chunks',
        contextChunksHint: 'Number of document chunks to retrieve for context. More chunks provide more context but may be slower.',
        ragSystem: 'RAG System',
        llmSystem: 'LLM System',
        actions: 'Actions',
        collection: 'Collection',
        documents: 'Documents',
        totalChunks: 'Total Chunks',
        embeddingModel: 'Embedding Model',
        service: 'Service',
        status: 'Status',
        available: 'Available',
        unavailable: 'Unavailable',
        baseUrl: 'Base URL',
        defaultModel: 'Default Model',
        availableModels: 'Available Models',
        noModels: 'No models available',
        selected: 'Selected',
        addModel: 'Add Model',
        pullNewModel: 'Pull New Model from Ollama',
        pullModelHint: 'Enter the name of any Ollama model to download and make it available. This may take several minutes depending on the model size.',
        modelNamePlaceholder: 'e.g., llama2, mistral, codellama',
        modelNameExample: 'Examples: llama2, llama2:13b, mistral, codellama:7b',
        pullModel: 'Pull Model',
        pulling: 'Pulling...',
        modelPullSuccess: 'Model "{{model}}" pulled successfully!',
        modelPullError: 'Failed to pull model: {{error}}',
        resetRag: 'Reset RAG Collection',
        resetRagHint: 'This will delete all document embeddings. Uploaded files will remain but need to be reprocessed.',
        resetRagConfirm: 'Are you sure you want to reset the RAG collection? This will delete all document embeddings.',
        refreshSettings: 'Refresh Settings',
        languageSaved: 'Language preference saved!',
        llmLanguageSaved: 'LLM language preference saved!',
        modelSaved: 'Model preference saved!',
        chunksSaved: 'Chunks preference saved!',
        ragResetSuccess: 'RAG collection reset successfully!',
        ragResetError: 'Failed to reset RAG collection.'
      },

      // Language Options
      languages: {
        auto: 'Auto-detect',
        english: 'English',
        spanish: 'Spanish'
      },

      // Chunks Options
      chunks: {
        chunk: 'chunk',
        chunks: 'chunks'
      }
    }
  },
  es: {
    translation: {
      // Header
      appTitle: 'Asistente de Planificación de Estudios',

      // Navigation
      nav: {
        home: 'Inicio',
        files: 'Archivos',
        settings: 'Configuración'
      },

      // Authentication
      auth: {
        welcome: 'Bienvenido al Asistente de Planificación de Estudios',
        subtitle: 'Tu compañero inteligente para materiales de estudio y planificación',
        features: 'Características',
        feature1: 'Sube y organiza tus documentos de estudio',
        feature2: 'Haz preguntas con la ayuda de IA',
        feature3: 'Obtén asistencia de aprendizaje personalizada',
        loginButton: 'Iniciar Sesión con Auth0',
        securedBy: 'Protegido por',
        loading: 'Cargando...',
        checking: 'Verificando autenticación...',
        logout: 'Cerrar Sesión'
      },

      // Home Page
      home: {
        title: 'Haz Preguntas Sobre Tus Documentos',
        noMessages: '¡Aún no hay mensajes. Haz una pregunta sobre tus documentos!',
        configureSettings: 'Configura tus preferencias en la pestaña de Configuración',
        placeholder: 'Haz una pregunta sobre tus documentos...',
        send: 'Enviar',
        clearChat: 'Limpiar Chat',
        thinking: 'Pensando...',
        sources: 'Fuentes',
        model: 'Modelo',
        useRAG: 'Usar RAG (Generación Aumentada con Recuperación)',
        ragEnabled: 'Las consultas usarán el contexto de los documentos',
        ragDisabled: 'Consultas directas al LLM sin documentos'
      },

      // Files Page
      files: {
        uploadTitle: 'Subir Material de Estudio',
        manageTitle: 'Administrar Archivos',
        uploadHint: 'Haz clic o arrastra un archivo para subir',
        uploadHintSelected: 'Tamaño',
        supportedFormats: 'Soporta archivos PDF, Word, Excel, Texto y Markdown',
        uploadButton: 'Subir Archivo',
        cancel: 'Cancelar',
        uploading: 'Subiendo...',
        refresh: 'Actualizar',
        delete: 'Eliminar',
        deleting: 'Eliminando...',
        noFiles: 'Aún no hay archivos subidos',
        noFilesHint: 'Sube algunos documentos para comenzar',
        totalFiles: 'Total de archivos',
        uploaded: 'Subido',
        maxFileSize: 'Tamaño máximo de archivo',
        unsupported: 'Tipo de archivo no soportado para procesamiento RAG',
        uploadSuccess: '¡Archivo subido y procesado exitosamente!',
        uploadSuccessNoRag: 'Archivo subido pero no pudo ser procesado para RAG.',
        uploadError: 'Fallo al subir. Por favor intenta de nuevo.',
        deleteConfirm: '¿Estás seguro de que quieres eliminar',
        deleteSuccess: 'eliminado exitosamente.',
        deleteError: 'Fallo al eliminar'
      },

      // Settings Page
      settings: {
        title: 'Configuración del Sistema',
        userPreferences: 'Preferencias de Usuario',
        defaultLanguage: 'Idioma',
        languageHint: 'Idioma para la interfaz y las respuestas del LLM.',
        preferredModel: 'Modelo LLM Preferido',
        preferredModelHint: 'Haz clic en un modelo abajo para seleccionarlo.',
        useRAG: 'Usar RAG (Generación Aumentada con Recuperación)',
        useRAGHint: 'Cuando está activado, las consultas buscarán en tus documentos y usarán su contenido como contexto para las respuestas.',
        ragSaved: '¡Preferencia de RAG guardada!',
        contextChunks: 'Número de Fragmentos de Contexto',
        contextChunksHint: 'Número de fragmentos de documentos a recuperar para contexto. Más fragmentos proporcionan más contexto pero pueden ser más lentos.',
        ragSystem: 'Sistema RAG',
        llmSystem: 'Sistema LLM',
        actions: 'Acciones',
        collection: 'Colección',
        documents: 'Documentos',
        totalChunks: 'Total de Fragmentos',
        embeddingModel: 'Modelo de Embeddings',
        service: 'Servicio',
        status: 'Estado',
        available: 'Disponible',
        unavailable: 'No disponible',
        baseUrl: 'URL Base',
        defaultModel: 'Modelo Predeterminado',
        availableModels: 'Modelos Disponibles',
        noModels: 'No hay modelos disponibles',
        selected: 'Seleccionado',
        addModel: 'Añadir Modelo',
        pullNewModel: 'Descargar Nuevo Modelo de Ollama',
        pullModelHint: 'Ingresa el nombre de cualquier modelo de Ollama para descargarlo y hacerlo disponible. Esto puede tomar varios minutos dependiendo del tamaño del modelo.',
        modelNamePlaceholder: 'ej., llama2, mistral, codellama',
        modelNameExample: 'Ejemplos: llama2, llama2:13b, mistral, codellama:7b',
        pullModel: 'Descargar Modelo',
        pulling: 'Descargando...',
        modelPullSuccess: '¡Modelo "{{model}}" descargado exitosamente!',
        modelPullError: 'Error al descargar modelo: {{error}}',
        resetRag: 'Resetear Colección RAG',
        resetRagHint: 'Esto eliminará todos los embeddings de documentos. Los archivos subidos permanecerán pero necesitarán ser reprocesados.',
        resetRagConfirm: '¿Estás seguro de que quieres resetear la colección RAG? Esto eliminará todos los embeddings de documentos.',
        refreshSettings: 'Actualizar Configuración',
        languageSaved: '¡Preferencia de idioma guardada!',
        llmLanguageSaved: '¡Preferencia de idioma LLM guardada!',
        modelSaved: '¡Preferencia de modelo guardada!',
        chunksSaved: '¡Preferencia de fragmentos guardada!',
        ragResetSuccess: '¡Colección RAG reseteada exitosamente!',
        ragResetError: 'Fallo al resetear la colección RAG.'
      },

      // Language Options
      languages: {
        auto: 'Auto-detectar',
        english: 'Inglés',
        spanish: 'Español'
      },

      // Chunks Options
      chunks: {
        chunk: 'fragmento',
        chunks: 'fragmentos'
      }
    }
  }
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: localStorage.getItem('interfaceLanguage') || 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;
