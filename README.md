# RAG Bank Assistant

Asistente conversacional basado en RAG (Retrieval-Augmented Generation) con Web Scraping para BBVA Colombia.

## Descripción

Este sistema permite consultar información publicada en el sitio web institucional de BBVA (o cualquier banco) mediante una interfaz conversacional, combinando scraping, vectorización, almacenamiento y recuperación aumentada con LLM.

## Requisitos previos

- Docker y Docker Compose instalados
- (Opcional) Python 3.10+ para desarrollo local
- Acceso a internet para descargar imágenes y dependencias

## Instalación y despliegue

1. Clona el repositorio:
   ```bash
   git clone https://github.com/SebastVR/rag-data-assistant-ia.git
   cd rag-data-assistant-ia
   ```

2. Crea un archivo `.env` en la raíz (puedes copiar `.env.example` y ajustar credenciales de Postgres, Minio, etc).
   
3. Descarga el modelo Llama 2 (llama-2-7b-chat.Q4_K_M.gguf) desde Hugging Face y colócalo en la carpeta `app/rag/`:
   - [https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF](https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF)
   - El archivo debe llamarse exactamente `llama-2-7b-chat.Q4_K_M.gguf` y ubicarse en `app/rag/llama-2-7b-chat.Q4_K_M.gguf`.
   
   > Si no tienes cuenta en Hugging Face, deberás crear una para poder descargar el modelo.

4. Levanta todos los servicios con Docker Compose:
   ```bash
   docker compose up --build
   ```

   Esto iniciará:
   - API FastAPI (puerto 80)
   - Interfaz Streamlit (puerto 8501)
   - Qdrant (vector store, puerto 6333)
   - Postgres (puerto 5432)
   - Redis, RabbitMQ, Minio, Celery worker y Flower

4. Para detener los servicios:
   ```bash
   docker compose down
   ```

## Uso de la interfaz conversacional

- Accede a la UI en [http://localhost:8501](http://localhost:8501)
- Puedes iniciar nuevas conversaciones, hacer preguntas sobre el contenido scrapeado y visualizar analíticas de uso y costos.
- El historial de conversación se mantiene por sesión y es configurable.

## Stack tecnológico y justificación

- **Python 3.10+**: Lenguaje principal, soporte para FastAPI, Celery, etc.
- **FastAPI**: API REST moderna, rápida y tipada.
- **Streamlit**: UI web minimalista y rápida de desarrollar.
- **Qdrant**: Base de datos vectorial open source, self-hosted.
- **Postgres**: Almacenamiento estructurado y persistencia de conversaciones.
- **Celery + Redis + RabbitMQ**: Tareas asíncronas y procesamiento distribuido.
- **Minio**: Almacenamiento S3 compatible para archivos y datos crudos.
- **Docker Compose**: Orquestación de todos los servicios con un solo comando.

## Patrones de diseño implementados

1. **Factory Pattern (Creacional)**  
   - Usado en la inicialización de modelos de lenguaje y componentes de scraping, permitiendo instanciar diferentes clases según configuración.

2. **Strategy Pattern (Comportamental)**  
   - Aplicado en la selección de métodos de vectorización y pipelines de procesamiento, permitiendo intercambiar algoritmos sin modificar el flujo principal.

3. **Singleton Pattern (Creacional/Estructural)**  
   - Utilizado para la gestión de la conexión a la base de datos y clientes de servicios externos, asegurando una única instancia global.

4. **Adapter Pattern (Estructural)**  
   - Usado para integrar servicios externos (Minio, Qdrant, S3, etc.), adaptando sus interfaces a las necesidades internas del sistema.

5. **Facade Pattern (Estructural)**  
   - Implementado en servicios y controladores que exponen una interfaz simplificada para operaciones complejas (por ejemplo, scraping y pipeline RAG).

6. **Observer Pattern (Comportamental)**  
   - Utilizado en la gestión de eventos y tareas asíncronas con Celery, donde los workers reaccionan a eventos de la cola.

*(Ver detalles y ejemplos en los módulos `llm/`, `db/`, `scraping/`, y servicios de integración)*

## Limitaciones y decisiones de diseño

- El scraping está enfocado en HTML público; cambios en la estructura del sitio pueden requerir ajustes.
- El sistema asume que los endpoints de la API y la UI corren en la misma red Docker.
- Los tests automáticos cubren endpoints principales, pero pueden ampliarse.
- El frontend de Streamlit es funcional, pero minimalista.

## Futuras mejoras

- Completar y ampliar la cobertura de tests automáticos.
- Integrar CI/CD para pruebas y despliegue automático.
- Mejorar la experiencia de usuario en la UI (diseño, validaciones, feedback).
- Documentar y visualizar mejor las analíticas y logs.
- Añadir soporte para scraping incremental y monitoreo de cambios.
- Generar un informe técnico detallado de arquitectura y decisiones.
- Soporte multi-idioma y multi-sitio.

## Métricas y analítica

- El sistema expone paneles de analítica en la UI: número de documentos, chunks, costos, latencia, uso por modelo, etc.
- Se pueden extraer métricas del histórico de conversaciones para análisis de impacto.

## Variables de entorno

- Ver `.env.example` para la lista completa de variables requeridas (DB, S3, Qdrant, etc).
- Parámetros como el número de mensajes de historial, modelo LLM, chunk size, etc., son configurables vía entorno.

## Ejecución de tests

```bash
docker compose exec app pytest -q
```

## Contribución

- Sigue la convención de commits granular y descriptiva (un commit por archivo/cambio relevante).
- Añade tests y documentación para nuevas funcionalidades.
- Abre issues o PRs para sugerencias y mejoras.

## Notas y supuestos

- Si algún requerimiento no se implementó completamente, está documentado aquí y en los TODOs del código.

## Servicios, puertos y descripción de cada microservicio

| Servicio      | URL de acceso                        | Puerto | Descripción                                                                 |
|---------------|--------------------------------------|--------|-----------------------------------------------------------------------------|
| API FastAPI   | http://localhost:80/docs             | 80     | API principal RESTful y documentación Swagger. Permite interactuar con el backend, endpoints de scraping, RAG, analítica, etc. |
| Minio         | http://localhost:9001/browser/       | 9001   | Consola web de Minio (almacenamiento S3 compatible) para archivos crudos y procesados. |
| Qdrant        | http://localhost:6333/dashboard#/collections | 6333   | Dashboard de la base de datos vectorial Qdrant, gestión de colecciones y vectores. |
| Flower        | http://localhost:5555/               | 5555   | Monitorización de tareas asíncronas Celery (workers, colas, tareas en tiempo real). |
| Streamlit UI  | http://localhost:8501/               | 8501   | Interfaz web para usuarios finales: chat, historial, analítica y métricas.   |

### Resumen de cada microservicio

- **API FastAPI**: Expone todos los endpoints RESTful para scraping, consulta RAG, gestión de conversaciones, analítica y administración. Incluye documentación interactiva en `/docs`.
- **Minio**: Proporciona almacenamiento de objetos compatible con S3, usado para guardar archivos crudos y procesados del scraping.
- **Qdrant**: Base de datos vectorial para indexar y buscar embeddings de los documentos extraídos. Permite búsquedas semánticas eficientes.
- **Flower**: Herramienta de monitoreo para Celery, muestra el estado de los workers, tareas ejecutadas, pendientes y estadísticas de procesamiento.
- **Streamlit UI**: Interfaz web minimalista para interactuar con el sistema, realizar preguntas, ver historial y métricas de uso/costos.

> Todos los servicios se levantan automáticamente con `docker compose up --build` y pueden ser accedidos en los puertos indicados.

## Estructura del proyecto

```
rag-data-assistant-ia/
├── app/
│   ├── main.py                # Punto de entrada FastAPI
│   ├── ui/                    # Interfaz Streamlit
│   ├── scraping/              # Lógica de scraping web
│   ├── rag/                   # Pipelines RAG, embeddings, reranker
│   ├── models/                # Modelos ORM y Pydantic
│   ├── db/                    # Conexión y utilidades de base de datos
│   ├── services/              # Integraciones externas y lógica de negocio
│   ├── schemas/               # Schemas de validación y serialización
│   ├── routers/               # Rutas y endpoints de la API
│   ├── celery_worker/         # Configuración y tareas Celery
│   ├── util/                  # Utilidades generales
│   └── tests/                 # Pruebas automáticas
├── docker-compose.yml         # Orquestación de servicios
├── Dockerfile                 # Imagen base de la app
├── requirements.txt           # Dependencias Python
├── .env.example               # Variables de entorno de ejemplo
└── README.md                  # Documentación principal
```

## Ejemplo de uso rápido

- **Acceso vía UI:**
  1. Ve a [http://localhost:8501](http://localhost:8501)
  2. Haz clic en "+ Nueva conversacion" y escribe tu pregunta.
  3. Visualiza la respuesta y el historial en la misma pantalla.

- **Acceso vía API (ejemplo con curl):**
  ```bash
  curl -X POST http://localhost:80/api/v1/rag/query \
    -H 'Content-Type: application/json' \
    -d '{"question": "¿Qué es el RAG?", "use_rerank": true}'
  ```

## Cobertura de tests

Actualmente existen pruebas automáticas para los endpoints principales de la API y para el scraping. Se recomienda ampliar la cobertura para casos de error, validaciones y flujos alternativos.

## Supuestos y decisiones

- El scraping se realiza sobre HTML público y puede requerir ajustes si la estructura del sitio cambia.
- Se priorizó el uso de tecnologías open source y gratuitas.
- El sistema está pensado para ser ejecutado en entornos Dockerizados.
- Si algún requerimiento no se implementó completamente, está documentado aquí y en los TODOs del código.

## Licencia

Este proyecto se distribuye bajo la licencia MIT. Puedes usarlo, modificarlo y distribuirlo libremente.

## Contacto y soporte

Para reportar problemas, sugerencias o solicitar soporte, abre un issue en el repositorio o contacta al autor vía GitHub.
