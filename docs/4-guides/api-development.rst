API Development
===============

This guide helps you choose the right API approach for your Django backend. The template ships with Django REST Framework by default, but GraphQL and django-ninja are viable alternatives depending on your requirements.

Overview
--------

Your API layer sits between HTTP requests and your service layer (see :doc:`service-layer-patterns`). The choice of API framework affects:

- How you define request/response schemas
- Authentication and permission patterns
- OpenAPI documentation generation
- Async support and performance characteristics

The template's ``use_drf`` option enables Django REST Framework with drf-spectacular for OpenAPI generation. For frontend type safety with DRF, see :doc:`type-safe-api-integration`.

Django REST Framework (Default)
-------------------------------

DRF is the template's default choice for good reasons: it's battle-tested, has the largest ecosystem, and integrates seamlessly with Django's authentication and ORM.

Why DRF
^^^^^^^

- **Mature ecosystem**: Authentication backends, pagination, filtering, throttling all built-in or available as packages
- **Browsable API**: Interactive documentation useful during development
- **Serializers**: Declarative request/response validation with ORM integration
- **drf-spectacular**: First-class OpenAPI 3.0 generation for type-safe frontend clients

When to Use
^^^^^^^^^^^

DRF is the right choice for most projects, especially:

- CRUD-heavy applications
- Projects requiring extensive authentication options (OAuth, JWT, session, token)
- Teams familiar with Django patterns
- Applications where OpenAPI documentation is important

Basic Pattern
^^^^^^^^^^^^^

With the services pattern, views become thin orchestration layers:

.. code-block:: python

    # {project_slug}/tasks/api/serializers.py
    from rest_framework import serializers

    class TaskCreateInputSerializer(serializers.Serializer):
        title = serializers.CharField(max_length=200)
        description = serializers.CharField(required=False)

    class TaskSerializer(serializers.Serializer):
        id = serializers.IntegerField(read_only=True)
        title = serializers.CharField()
        description = serializers.CharField()
        status = serializers.CharField()
        created_at = serializers.DateTimeField()


    # {project_slug}/tasks/api/views.py
    from rest_framework import status
    from rest_framework.response import Response
    from rest_framework.views import APIView

    from {project_slug}.tasks.services import task_create
    from {project_slug}.tasks.selectors import task_list
    from .serializers import TaskCreateInputSerializer, TaskSerializer

    class TaskListCreateView(APIView):
        def get(self, request):
            tasks = task_list(fetched_by=request.user)
            return Response(TaskSerializer(tasks, many=True).data)

        def post(self, request):
            serializer = TaskCreateInputSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            task = task_create(
                created_by=request.user,
                **serializer.validated_data,
            )

            return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)

GraphQL
-------

GraphQL offers a query language that lets clients request exactly the data they need. Consider it when your data relationships are complex or client needs vary significantly.

When to Consider
^^^^^^^^^^^^^^^^

- **Complex data graphs**: Deeply nested relationships where REST would require multiple round-trips
- **Diverse clients**: Mobile and web apps with different data requirements from the same backend
- **API aggregation**: Unifying multiple data sources behind a single endpoint
- **Rapid iteration**: Frontend teams need flexibility without backend changes for each new view

Trade-offs
^^^^^^^^^^

+---------------------------+------------------------------------------+
| Advantage                 | Consideration                            |
+===========================+==========================================+
| Flexible queries          | HTTP caching is harder (POST requests)   |
+---------------------------+------------------------------------------+
| Single endpoint           | N+1 query problems require careful       |
|                           | attention (use DataLoader)               |
+---------------------------+------------------------------------------+
| Strong typing             | Learning curve for teams new to GraphQL  |
+---------------------------+------------------------------------------+
| Self-documenting schema   | Tooling less mature than REST ecosystem  |
+---------------------------+------------------------------------------+

Library Options
^^^^^^^^^^^^^^^

**graphene-django**
    The established choice with Django ORM integration, relay support, and extensive documentation. Sync-only.

    - `graphene-django documentation <https://docs.graphene-python.org/projects/django/en/latest/>`_

**strawberry-graphql**
    Modern, async-native library with type hints and dataclass-based schema definition. Better fit for async Django deployments.

    - `Strawberry documentation <https://strawberry.rocks/docs/integrations/django>`_

Adding GraphQL to Your Project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

GraphQL is not included in the generated template. To add it:

1. Install your chosen library (``pip install graphene-django`` or ``pip install strawberry-graphql[django]``)
2. Add to ``INSTALLED_APPS``
3. Define your schema in each module (e.g., ``{project_slug}/tasks/graphql/schema.py``)
4. Mount the GraphQL endpoint in ``config/urls.py``

.. note::

    GraphQL support as a template option is on the roadmap. See :doc:`/6-about/roadmap`.

django-ninja
------------

django-ninja brings FastAPI's developer experience to Django: type hints for validation, automatic OpenAPI generation, and native async support.

When to Consider
^^^^^^^^^^^^^^^^

- **Async-first**: Your application heavily uses async views and you want ``use_async=y`` benefits throughout
- **FastAPI familiarity**: Team has FastAPI experience and prefers that API style
- **Pydantic validation**: You want Pydantic models for request/response validation
- **Performance-critical**: Async endpoints for I/O-bound operations

Strengths
^^^^^^^^^

- **Native async**: Built for async from the ground up
- **Type-hint validation**: Request bodies, query params, and path params validated via type hints
- **Built-in OpenAPI**: Automatic schema generation without additional packages
- **Familiar syntax**: Similar to FastAPI, lower learning curve for those with that background

Trade-offs
^^^^^^^^^^

+---------------------------+------------------------------------------+
| Advantage                 | Consideration                            |
+===========================+==========================================+
| Async native              | Smaller ecosystem than DRF               |
+---------------------------+------------------------------------------+
| Type-hint validation      | Less Django ORM integration (no          |
|                           | ModelSerializer equivalent)              |
+---------------------------+------------------------------------------+
| FastAPI-like syntax       | Fewer third-party extensions             |
+---------------------------+------------------------------------------+
| Built-in OpenAPI          | Community and documentation smaller      |
+---------------------------+------------------------------------------+

Basic Pattern
^^^^^^^^^^^^^

.. code-block:: python

    # {project_slug}/tasks/api/routes.py
    from ninja import Router, Schema
    from typing import List

    from {project_slug}.tasks.services import task_create
    from {project_slug}.tasks.selectors import task_list

    router = Router()

    class TaskIn(Schema):
        title: str
        description: str = ""

    class TaskOut(Schema):
        id: int
        title: str
        description: str
        status: str

    @router.get("/", response=List[TaskOut])
    def list_tasks(request):
        return task_list(fetched_by=request.user)

    @router.post("/", response=TaskOut)
    def create_task(request, payload: TaskIn):
        return task_create(
            created_by=request.user,
            title=payload.title,
            description=payload.description,
        )

Adding django-ninja to Your Project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

django-ninja is not included in the generated template. To add it:

1. Install: ``pip install django-ninja``
2. Create routers in each module
3. Mount the NinjaAPI in ``config/urls.py``

.. code-block:: python

    # config/urls.py
    from ninja import NinjaAPI

    api = NinjaAPI()
    api.add_router("/tasks/", "myproject.tasks.api.routes.router")

    urlpatterns = [
        path("api/", api.urls),
        # ...
    ]

.. note::

    django-ninja support as a template option is on the roadmap. See :doc:`/6-about/roadmap`.

Choosing the Right Approach
---------------------------

Use this matrix to guide your decision:

+---------------------+------------------+-------------------+------------------+
| Consideration       | DRF              | GraphQL           | django-ninja     |
+=====================+==================+===================+==================+
| Async native        | No (WSGI)        | Strawberry: Yes   | Yes              |
+---------------------+------------------+-------------------+------------------+
| Ecosystem size      | Largest          | Medium            | Growing          |
+---------------------+------------------+-------------------+------------------+
| OpenAPI generation  | Excellent        | N/A (own schema)  | Built-in         |
+---------------------+------------------+-------------------+------------------+
| Django ORM          | Deep integration | Good              | Manual mapping   |
| integration         |                  |                   |                  |
+---------------------+------------------+-------------------+------------------+
| Learning curve      | Moderate         | Steeper           | Lower (FastAPI)  |
+---------------------+------------------+-------------------+------------------+
| Best for            | Most apps        | Complex graphs    | Async-first      |
+---------------------+------------------+-------------------+------------------+

**Recommendation**: Start with DRF unless you have a specific reason not to. It's the safe default that works well for most Django applications. Consider alternatives when:

- GraphQL: Your frontend team specifically requests it, or you have genuinely complex data graph requirements
- django-ninja: You're building an async-first application and want that paradigm throughout your API layer

See Also
--------

- :doc:`type-safe-api-integration` — End-to-end type safety with DRF and React
- :doc:`service-layer-patterns` — Where business logic belongs (not in views)
- `Django REST Framework <https://www.django-rest-framework.org/>`_ — Official DRF documentation
- `graphene-django <https://docs.graphene-python.org/projects/django/en/latest/>`_ — GraphQL for Django
- `Strawberry <https://strawberry.rocks/>`_ — Async-native GraphQL
- `django-ninja <https://django-ninja.dev/>`_ — FastAPI-style APIs for Django
