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
        model: 'Model'
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
        '3': '3 chunks',
        '5': '5 chunks',
        '10': '10 chunks',
        '15': '15 chunks'
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
        model: 'Modelo'
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
        '3': '3 fragmentos',
        '5': '5 fragmentos',
        '10': '10 fragmentos',
        '15': '15 fragmentos'
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
