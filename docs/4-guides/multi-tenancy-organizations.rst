Multi-Tenancy with Organizations
================================

This guide explains how to implement organization-based multi-tenancy in your modular monolith, enabling a single codebase to serve multiple isolated tenants while supporting both shared SaaS and dedicated deployment modes.

Overview
--------

In B2B SaaS applications, **multi-tenancy** allows a single deployment to serve multiple organizations while keeping their data strictly isolated. Each organization sees only their data, and users of one organization cannot access another's resources.

This guide uses the **shared database with org_id** approach: all organizations' data lives in the same database tables, distinguished by foreign keys. This provides:

- **Operational simplicity**: Single database to backup, monitor, and maintain
- **Natural Django integration**: Works seamlessly with the ORM and migrations
- **Cross-tenant analytics**: Easy to run reports across all tenants when needed
- **Cost efficiency**: No per-tenant database overhead

The trade-off is that **every query must be filtered by organization**. This guide provides patterns to make this safe and ergonomic.

**Deployment modes:**

- **Shared SaaS**: Multiple organizations in a single deployment. Users can belong to multiple organizations and switch between them.
- **Dedicated**: Single organization per deployment. Typically for enterprise customers or self-hosted installations.

The Organizations App
---------------------

Following the modular monolith pattern, organizations are a separate Django app within your ``{project_slug}/`` directory.

Creating the App
^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Inside your project directory
    cd {project_slug}
    python ../manage.py startapp organizations

Your directory structure should look like:

.. code-block:: text

    {project_slug}/
    ├── users/
    ├── organizations/          # New app
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── managers.py         # Custom managers
    │   ├── middleware.py       # Organization context
    │   ├── migrations/
    │   ├── models.py
    │   ├── services.py         # Business logic
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── serializers.py
    │   │   └── views.py
    │   └── tests/
    │       ├── __init__.py
    │       ├── factories.py
    │       └── test_models.py
    ├── core/
    └── domain_events/

Registering the App
^^^^^^^^^^^^^^^^^^^

Add to ``config/settings/base.py``:

.. code-block:: python

    LOCAL_APPS = [
        "{project_slug}.users",
        "{project_slug}.organizations",  # Add this
        "{project_slug}.core",
        "{project_slug}.domain_events",
    ]

Models
------

The Organization Model
^^^^^^^^^^^^^^^^^^^^^^

The ``Organization`` model represents a tenant in your system:

.. code-block:: python

    # {project_slug}/organizations/models.py
    from django.db import models
    from django.utils.text import slugify

    from {project_slug}.core.models import BaseModel


    class Organization(BaseModel):
        """A tenant organization in the system."""

        name = models.CharField(max_length=255)
        slug = models.SlugField(max_length=255, unique=True, db_index=True)

        # Organization-level settings stored as JSON
        settings = models.JSONField(default=dict, blank=True)

        # Status
        is_active = models.BooleanField(default=True)

        class Meta:
            ordering = ["name"]

        def __str__(self) -> str:
            return self.name

        def save(self, *args, **kwargs):
            if not self.slug:
                self.slug = slugify(self.name)
            super().save(*args, **kwargs)

**Key fields:**

- ``slug``: URL-friendly identifier, indexed for fast lookups
- ``settings``: JSON field for per-org configuration (feature flags, limits, preferences)
- ``is_active``: Soft-disable organizations without deleting data

The OrganizationMember Model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Users can belong to multiple organizations with different roles:

.. code-block:: python

    # {project_slug}/organizations/models.py (continued)
    from django.conf import settings as django_settings


    class OrganizationRole(models.TextChoices):
        """Roles within an organization."""

        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"


    class OrganizationMember(BaseModel):
        """Membership linking a user to an organization with a role."""

        organization = models.ForeignKey(
            Organization,
            on_delete=models.CASCADE,
            related_name="memberships",
        )
        user = models.ForeignKey(
            django_settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name="organization_memberships",
        )
        role = models.CharField(
            max_length=20,
            choices=OrganizationRole.choices,
            default=OrganizationRole.MEMBER,
        )

        # Invitation tracking
        invited_by = models.ForeignKey(
            django_settings.AUTH_USER_MODEL,
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name="invitations_sent",
        )
        invited_at = models.DateTimeField(null=True, blank=True)
        joined_at = models.DateTimeField(auto_now_add=True)

        class Meta:
            unique_together = [("organization", "user")]
            ordering = ["-joined_at"]

        def __str__(self) -> str:
            return f"{self.user} - {self.organization} ({self.role})"

        @property
        def is_admin(self) -> bool:
            """Check if member has admin-level permissions."""
            return self.role in (OrganizationRole.OWNER, OrganizationRole.ADMIN)

**Role Permissions:**

+----------+----------------+----------------+--------------+---------------+
| Role     | Invite Members | Manage Members | View Billing | Delete Org    |
+==========+================+================+==============+===============+
| Owner    | Yes            | Yes            | Yes          | Yes           |
+----------+----------------+----------------+--------------+---------------+
| Admin    | Yes            | Yes            | Yes          | No            |
+----------+----------------+----------------+--------------+---------------+
| Member   | No             | No             | No           | No            |
+----------+----------------+----------------+--------------+---------------+
| Viewer   | No             | No             | No           | No            |
+----------+----------------+----------------+--------------+---------------+

Tenant-Scoped Base Model
^^^^^^^^^^^^^^^^^^^^^^^^

For models that belong to an organization, inherit from ``TenantModel``:

.. code-block:: python

    # {project_slug}/organizations/models.py (continued)

    class TenantModel(BaseModel):
        """Abstract base class for all organization-scoped models."""

        organization = models.ForeignKey(
            Organization,
            on_delete=models.CASCADE,
            related_name="%(class)s_set",
            db_index=True,
        )

        class Meta:
            abstract = True

**Usage example:**

.. code-block:: python

    # {project_slug}/projects/models.py
    from django.db import models

    from {project_slug}.organizations.models import TenantModel


    class Project(TenantModel):
        """A project belonging to an organization."""

        name = models.CharField(max_length=255)
        description = models.TextField(blank=True)

        class Meta:
            indexes = [
                models.Index(fields=["organization", "name"]),
            ]

The ``%(class)s_set`` pattern creates automatic related names (e.g., ``organization.project_set``). Always add compound indexes for efficient tenant-scoped queries.

Tenant Context
--------------

Every request needs to know which organization it's operating on behalf of. There are several approaches:

+------------------+---------------------+------------------------+------------------------+
| Approach         | Example             | Pros                   | Cons                   |
+==================+=====================+========================+========================+
| URL path         | ``/orgs/acme/...``  | Explicit, bookmarkable | Longer URLs            |
+------------------+---------------------+------------------------+------------------------+
| Subdomain        | ``acme.example.com``| Clean URLs             | DNS/SSL complexity     |
+------------------+---------------------+------------------------+------------------------+
| Session          | Session-stored      | Simple URLs            | Requires org switcher  |
+------------------+---------------------+------------------------+------------------------+
| HTTP Header      | ``X-Organization``  | Good for APIs          | Not for browser UI     |
+------------------+---------------------+------------------------+------------------------+

This guide uses **session-based context** with an org switch endpoint, combined with **header-based context** for API calls. This balances simplicity with flexibility.

Organization Middleware
^^^^^^^^^^^^^^^^^^^^^^^

Create middleware that attaches the current organization to each request:

.. code-block:: python

    # {project_slug}/organizations/middleware.py
    from django.conf import settings
    from django.http import HttpRequest

    from {project_slug}.organizations.models import Organization, OrganizationMember


    class OrganizationMiddleware:
        """
        Middleware that attaches the current organization to the request.

        Resolution order:
        1. X-Organization-Slug header (for API clients)
        2. Session-stored organization
        3. User's default organization (first membership)
        """

        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request: HttpRequest):
            request.organization = None

            if not request.user.is_authenticated:
                return self.get_response(request)

            # Dedicated mode: use configured organization
            if getattr(settings, "DEPLOYMENT_MODE", "saas") == "dedicated":
                request.organization = self._get_dedicated_organization()
            else:
                # SaaS mode: resolve from header/session
                org_slug = self._get_org_slug(request)
                if org_slug:
                    request.organization = self._resolve_organization(
                        request.user, org_slug
                    )
                if not request.organization:
                    request.organization = self._get_default_organization(request.user)

            return self.get_response(request)

        def _get_org_slug(self, request: HttpRequest) -> str | None:
            # API header takes precedence
            if header_slug := request.headers.get("X-Organization-Slug"):
                return header_slug
            # Fall back to session
            return request.session.get("current_organization_slug")

        def _resolve_organization(self, user, slug: str) -> Organization | None:
            """Resolve org slug to Organization, verifying user has access."""
            try:
                return Organization.objects.filter(
                    memberships__user=user,
                    slug=slug,
                    is_active=True,
                ).get()
            except Organization.DoesNotExist:
                return None

        def _get_default_organization(self, user) -> Organization | None:
            """Get user's first organization as default."""
            membership = (
                OrganizationMember.objects.filter(
                    user=user,
                    organization__is_active=True,
                )
                .select_related("organization")
                .first()
            )
            return membership.organization if membership else None

        def _get_dedicated_organization(self) -> Organization | None:
            """Get the single organization for dedicated deployments."""
            slug = getattr(settings, "DEDICATED_ORG_SLUG", None)
            if not slug:
                return None
            return Organization.objects.filter(slug=slug, is_active=True).first()

Register the middleware in ``config/settings/base.py``:

.. code-block:: python

    MIDDLEWARE = [
        "django.middleware.security.SecurityMiddleware",
        # ... other middleware ...
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "{project_slug}.organizations.middleware.OrganizationMiddleware",  # After auth
        # ...
    ]

Type Hints
^^^^^^^^^^

For better type safety, extend the request type:

.. code-block:: python

    # {project_slug}/organizations/types.py
    from django.http import HttpRequest

    from {project_slug}.organizations.models import Organization


    class OrganizationRequest(HttpRequest):
        """HttpRequest with organization context."""

        organization: Organization | None

Query Filtering
---------------

The most critical aspect of multi-tenancy is ensuring queries are always filtered by organization. **A single unfiltered query can leak data across tenants.**

Organization-Aware Manager
^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a custom manager that filters by the current organization:

.. code-block:: python

    # {project_slug}/organizations/managers.py
    from django.db import models


    class TenantManager(models.Manager):
        """Manager that filters querysets by organization."""

        def for_organization(self, organization):
            """Filter queryset to a specific organization."""
            return self.get_queryset().filter(organization=organization)

        def for_request(self, request):
            """Filter queryset based on request's organization context."""
            if not hasattr(request, "organization") or not request.organization:
                return self.none()
            return self.for_organization(request.organization)

Using the Manager
^^^^^^^^^^^^^^^^^

Apply the manager to tenant-scoped models:

.. code-block:: python

    # {project_slug}/projects/models.py
    from django.db import models

    from {project_slug}.organizations.managers import TenantManager
    from {project_slug}.organizations.models import TenantModel


    class Project(TenantModel):
        name = models.CharField(max_length=255)

        # Use tenant-aware manager
        objects = TenantManager()

        class Meta:
            indexes = [
                models.Index(fields=["organization", "name"]),
            ]

View Examples
^^^^^^^^^^^^^

In views, always use the tenant-filtered queryset:

.. code-block:: python

    # {project_slug}/projects/views.py
    from django.contrib.auth.mixins import LoginRequiredMixin
    from django.views.generic import ListView

    from {project_slug}.projects.models import Project


    class ProjectListView(LoginRequiredMixin, ListView):
        model = Project

        def get_queryset(self):
            return Project.objects.for_request(self.request)

For DRF ViewSets:

.. code-block:: python

    # {project_slug}/projects/api/views.py
    from rest_framework import viewsets

    from {project_slug}.projects.api.serializers import ProjectSerializer
    from {project_slug}.projects.models import Project


    class ProjectViewSet(viewsets.ModelViewSet):
        serializer_class = ProjectSerializer

        def get_queryset(self):
            return Project.objects.for_request(self.request)

        def perform_create(self, serializer):
            # Automatically set organization on create
            serializer.save(organization=self.request.organization)

.. warning::

    **Never use the default queryset without filtering.**

    .. code-block:: python

        # DANGEROUS - leaks data across tenants
        projects = Project.objects.all()

        # SAFE - always filter by organization
        projects = Project.objects.for_request(request)

    Consider writing a custom Django check or linter rule that flags unfiltered ``.all()`` calls on tenant models during development.

Deployment Modes
----------------

The same codebase can run in two modes controlled by environment variables:

Settings Configuration
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # config/settings/base.py

    # Deployment mode: "saas" or "dedicated"
    DEPLOYMENT_MODE = env("DEPLOYMENT_MODE", default="saas")

    # For dedicated mode, the single organization slug
    DEDICATED_ORG_SLUG = env("DEDICATED_ORG_SLUG", default=None)

    # Feature flags based on mode
    MULTI_ORG_ENABLED = DEPLOYMENT_MODE == "saas"

**Mode Behavior Differences:**

+------------------------+-----------------------------+-----------------------------+
| Feature                | Shared SaaS                 | Dedicated                   |
+========================+=============================+=============================+
| Organization picker    | Shown in UI                 | Hidden                      |
+------------------------+-----------------------------+-----------------------------+
| Create organization    | Users can create orgs       | Admin-only via CLI          |
+------------------------+-----------------------------+-----------------------------+
| Join organization      | Via invite link             | Automatic on signup         |
+------------------------+-----------------------------+-----------------------------+
| Org in URL/header      | Required for API calls      | Optional (auto-detected)    |
+------------------------+-----------------------------+-----------------------------+
| Cross-org reports      | Available to super-admin    | N/A                         |
+------------------------+-----------------------------+-----------------------------+

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

For shared SaaS deployment:

.. code-block:: bash

    DEPLOYMENT_MODE=saas

For dedicated deployment:

.. code-block:: bash

    DEPLOYMENT_MODE=dedicated
    DEDICATED_ORG_SLUG=acme-corp

Integration with Users
----------------------

The organizations module integrates with the existing users app through the membership model, not by modifying the User model itself.

User to Organizations Relationship
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Access user's organizations
    user.organization_memberships.all()

    # Get organizations where user is admin
    user.organization_memberships.filter(role__in=["owner", "admin"])

    # Check membership
    def user_belongs_to_org(user, organization) -> bool:
        return OrganizationMember.objects.filter(
            user=user,
            organization=organization,
        ).exists()

Adding Helper Methods to User
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Optionally add convenience methods to the User model:

.. code-block:: python

    # {project_slug}/users/models.py
    from django.contrib.auth.models import AbstractUser


    class User(AbstractUser):
        # ... existing fields ...

        def get_organizations(self):
            """Get all organizations this user belongs to."""
            from {project_slug}.organizations.models import Organization

            return Organization.objects.filter(memberships__user=self, is_active=True)

        def get_membership(self, organization):
            """Get membership for a specific organization."""
            return self.organization_memberships.filter(organization=organization).first()

        def has_org_role(self, organization, roles: list[str]) -> bool:
            """Check if user has one of the specified roles in an organization."""
            return self.organization_memberships.filter(
                organization=organization,
                role__in=roles,
            ).exists()

Domain Events Integration
-------------------------

Use domain events to decouple organization lifecycle from other modules. See :doc:`event-driven-architecture` for the full pattern.

Organization Events
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # {project_slug}/domain_events/events.py
    from {project_slug}.domain_events.base import DomainEvent


    class OrganizationCreatedEvent(DomainEvent):
        """Emitted when a new organization is created."""

        def __init__(self, organization_id: int, name: str, created_by_user_id: int):
            self.organization_id = organization_id
            self.name = name
            self.created_by_user_id = created_by_user_id


    class UserJoinedOrganizationEvent(DomainEvent):
        """Emitted when a user joins an organization."""

        def __init__(
            self,
            organization_id: int,
            user_id: int,
            role: str,
            invited_by_user_id: int | None,
        ):
            self.organization_id = organization_id
            self.user_id = user_id
            self.role = role
            self.invited_by_user_id = invited_by_user_id


    class UserLeftOrganizationEvent(DomainEvent):
        """Emitted when a user leaves or is removed from an organization."""

        def __init__(self, organization_id: int, user_id: int, reason: str):
            self.organization_id = organization_id
            self.user_id = user_id
            self.reason = reason  # "left", "removed", "org_deleted"

Publishing Events
^^^^^^^^^^^^^^^^^

Use a service class to encapsulate business logic and event publishing:

.. code-block:: python

    # {project_slug}/organizations/services.py
    from django.db import transaction

    from {project_slug}.domain_events.bus import event_bus
    from {project_slug}.domain_events.events import (
        OrganizationCreatedEvent,
        UserJoinedOrganizationEvent,
    )
    from {project_slug}.organizations.models import (
        Organization,
        OrganizationMember,
        OrganizationRole,
    )


    class OrganizationService:
        @classmethod
        @transaction.atomic
        def create_organization(cls, name: str, created_by) -> Organization:
            """Create a new organization with the creator as owner."""
            org = Organization.objects.create(name=name)

            # Creator becomes owner
            OrganizationMember.objects.create(
                organization=org,
                user=created_by,
                role=OrganizationRole.OWNER,
            )

            # Publish event after transaction commits
            def _publish():
                event_bus.publish(
                    OrganizationCreatedEvent(
                        organization_id=org.id,
                        name=org.name,
                        created_by_user_id=created_by.id,
                    )
                )

            transaction.on_commit(_publish)

            return org

        @classmethod
        @transaction.atomic
        def add_member(
            cls,
            organization: Organization,
            user,
            role: str = OrganizationRole.MEMBER,
            invited_by=None,
        ) -> OrganizationMember:
            """Add a user to an organization."""
            from django.utils import timezone

            membership = OrganizationMember.objects.create(
                organization=organization,
                user=user,
                role=role,
                invited_by=invited_by,
                invited_at=timezone.now() if invited_by else None,
            )

            def _publish():
                event_bus.publish(
                    UserJoinedOrganizationEvent(
                        organization_id=organization.id,
                        user_id=user.id,
                        role=role,
                        invited_by_user_id=invited_by.id if invited_by else None,
                    )
                )

            transaction.on_commit(_publish)

            return membership

API Endpoints
-------------

Register organization endpoints in the API router.

Serializers
^^^^^^^^^^^

.. code-block:: python

    # {project_slug}/organizations/api/serializers.py
    from rest_framework import serializers

    from {project_slug}.organizations.models import Organization, OrganizationMember


    class OrganizationSerializer(serializers.ModelSerializer):
        class Meta:
            model = Organization
            fields = ["id", "name", "slug", "created_at"]
            read_only_fields = ["slug", "created_at"]


    class OrganizationMemberSerializer(serializers.ModelSerializer):
        user_email = serializers.EmailField(source="user.email", read_only=True)
        user_name = serializers.CharField(source="user.name", read_only=True)

        class Meta:
            model = OrganizationMember
            fields = ["id", "user", "user_email", "user_name", "role", "joined_at"]
            read_only_fields = ["joined_at"]

ViewSets
^^^^^^^^

.. code-block:: python

    # {project_slug}/organizations/api/views.py
    from rest_framework import permissions, status, viewsets
    from rest_framework.decorators import action
    from rest_framework.response import Response

    from {project_slug}.organizations.api.serializers import (
        OrganizationMemberSerializer,
        OrganizationSerializer,
    )
    from {project_slug}.organizations.models import Organization, OrganizationMember


    class OrganizationViewSet(viewsets.ModelViewSet):
        serializer_class = OrganizationSerializer
        permission_classes = [permissions.IsAuthenticated]

        def get_queryset(self):
            # Users only see organizations they belong to
            return Organization.objects.filter(
                memberships__user=self.request.user,
                is_active=True,
            )

        @action(detail=True, methods=["post"])
        def switch(self, request, pk=None):
            """Switch to this organization (stores in session)."""
            org = self.get_object()
            request.session["current_organization_slug"] = org.slug
            return Response({"status": "switched", "organization": org.slug})

        @action(detail=False)
        def current(self, request):
            """Get the current organization context."""
            if not request.organization:
                return Response(
                    {"error": "No organization context"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = self.get_serializer(request.organization)
            return Response(serializer.data)

        @action(detail=True)
        def members(self, request, pk=None):
            """List members of an organization."""
            org = self.get_object()
            members = OrganizationMember.objects.filter(organization=org)
            serializer = OrganizationMemberSerializer(members, many=True)
            return Response(serializer.data)

Router Registration
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # config/api_router.py
    from {project_slug}.organizations.api.views import OrganizationViewSet

    router.register("organizations", OrganizationViewSet, basename="organization")

Testing Patterns
----------------

Testing multi-tenant code requires verifying data isolation between organizations.

Test Factories
^^^^^^^^^^^^^^

.. code-block:: python

    # {project_slug}/organizations/tests/factories.py
    import factory
    from django.utils.text import slugify
    from factory.django import DjangoModelFactory

    from {project_slug}.organizations.models import (
        Organization,
        OrganizationMember,
        OrganizationRole,
    )
    from {project_slug}.users.tests.factories import UserFactory


    class OrganizationFactory(DjangoModelFactory):
        name = factory.Faker("company")
        slug = factory.LazyAttribute(lambda o: slugify(o.name))

        class Meta:
            model = Organization
            django_get_or_create = ["slug"]


    class OrganizationMemberFactory(DjangoModelFactory):
        organization = factory.SubFactory(OrganizationFactory)
        user = factory.SubFactory(UserFactory)
        role = OrganizationRole.MEMBER

        class Meta:
            model = OrganizationMember

Conftest Fixtures
^^^^^^^^^^^^^^^^^

.. code-block:: python

    # {project_slug}/conftest.py (add to existing)
    import pytest

    from {project_slug}.organizations.tests.factories import (
        OrganizationFactory,
        OrganizationMemberFactory,
    )


    @pytest.fixture
    def organization(db):
        return OrganizationFactory()


    @pytest.fixture
    def user_with_org(db, user):
        """User with organization membership."""
        org = OrganizationFactory()
        OrganizationMemberFactory(user=user, organization=org, role="owner")
        return user, org


    @pytest.fixture
    def request_with_org(rf, user_with_org):
        """Request factory with organization context."""
        user, org = user_with_org
        request = rf.get("/")
        request.user = user
        request.organization = org
        return request

Testing Data Isolation
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # {project_slug}/projects/tests/test_isolation.py
    import pytest

    from {project_slug}.organizations.tests.factories import OrganizationFactory
    from {project_slug}.projects.models import Project


    @pytest.mark.django_db
    class TestTenantIsolation:
        def test_projects_isolated_by_organization(self):
            """Projects from one org should not appear in another's queries."""
            org_a = OrganizationFactory(name="Org A")
            org_b = OrganizationFactory(name="Org B")

            # Create projects in each org
            project_a = Project.objects.create(organization=org_a, name="Project A")
            project_b = Project.objects.create(organization=org_b, name="Project B")

            # Query for org_a should only return its projects
            org_a_projects = Project.objects.for_organization(org_a)
            assert list(org_a_projects) == [project_a]

            # Query for org_b should only return its projects
            org_b_projects = Project.objects.for_organization(org_b)
            assert list(org_b_projects) == [project_b]

        def test_for_request_returns_empty_without_org(self, rf, user):
            """for_request returns empty queryset when no organization context."""
            OrganizationFactory()
            Project.objects.create(
                organization=OrganizationFactory(), name="Some Project"
            )

            request = rf.get("/")
            request.user = user
            request.organization = None

            # Should return empty queryset, not raise an error
            projects = Project.objects.for_request(request)
            assert projects.count() == 0

        def test_cannot_access_other_org_project_by_pk(self, client, user_with_org):
            """User cannot access resources from organizations they don't belong to."""
            user, org_a = user_with_org
            org_b = OrganizationFactory(name="Other Org")
            secret_project = Project.objects.create(
                organization=org_b, name="Secret Project"
            )

            client.force_login(user)
            response = client.get(f"/api/projects/{secret_project.id}/")

            assert response.status_code == 404

Common Pitfalls and Security
----------------------------

Unfiltered Queries
^^^^^^^^^^^^^^^^^^

The most common and dangerous mistake is forgetting to filter queries:

.. code-block:: python

    # WRONG: Returns all projects across all organizations
    def get_all_projects():
        return Project.objects.all()

    # RIGHT: Always filter by organization
    def get_projects(request):
        return Project.objects.for_request(request)

**Mitigation strategies:**

1. Use a linter or custom Django check to flag ``.all()`` on tenant models
2. Override the default manager to require explicit filtering
3. Add logging for unfiltered queries in development

Object-Level Permission Checks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Don't rely solely on queryset filtering. Add explicit checks:

.. code-block:: python

    from rest_framework.exceptions import PermissionDenied


    class ProjectViewSet(viewsets.ModelViewSet):
        def get_queryset(self):
            return Project.objects.for_request(self.request)

        def get_object(self):
            obj = super().get_object()
            # Double-check organization access
            if obj.organization != self.request.organization:
                raise PermissionDenied("Access denied")
            return obj

Bulk Operations
^^^^^^^^^^^^^^^

Be careful with bulk operations:

.. code-block:: python

    # DANGEROUS: Could update projects across organizations
    Project.objects.filter(status="draft").update(status="active")

    # SAFE: Always scope to organization
    Project.objects.for_organization(org).filter(status="draft").update(status="active")

Related Object Queries
^^^^^^^^^^^^^^^^^^^^^^

When traversing relationships, ensure you don't leak into other organizations:

.. code-block:: python

    # DANGEROUS: task.project could belong to different org
    def get_task_project_name(task):
        return task.project.name

    # SAFE: Verify organization matches
    def get_task_project_name(task, organization):
        if task.organization != organization:
            raise PermissionDenied("Access denied")
        return task.project.name

Django Admin
^^^^^^^^^^^^

The Django admin bypasses your custom managers. Add organization filtering:

.. code-block:: python

    # {project_slug}/organizations/admin.py
    from django.contrib import admin

    from {project_slug}.organizations.models import Organization, OrganizationMember


    @admin.register(Organization)
    class OrganizationAdmin(admin.ModelAdmin):
        list_display = ["name", "slug", "is_active", "created_at"]
        search_fields = ["name", "slug"]
        list_filter = ["is_active"]


    @admin.register(OrganizationMember)
    class OrganizationMemberAdmin(admin.ModelAdmin):
        list_display = ["user", "organization", "role", "joined_at"]
        list_filter = ["role", "organization"]


    class TenantModelAdmin(admin.ModelAdmin):
        """Base admin for tenant-scoped models."""

        def get_queryset(self, request):
            qs = super().get_queryset(request)
            # Superusers see all; others see only their orgs
            if request.user.is_superuser:
                return qs
            user_orgs = request.user.organization_memberships.values_list(
                "organization_id", flat=True
            )
            return qs.filter(organization_id__in=user_orgs)

Summary
-------

1. **Organizations as Tenants**: The ``Organization`` model represents tenants; ``OrganizationMember`` links users with roles via a many-to-many relationship.

2. **TenantModel Base Class**: Inherit from ``TenantModel`` for all organization-scoped models to ensure consistent foreign key patterns and indexing.

3. **Middleware for Context**: ``OrganizationMiddleware`` attaches ``request.organization`` based on HTTP headers, session, or default membership.

4. **Always Filter Queries**: Use ``TenantManager.for_request()`` or ``for_organization()`` to ensure queries are scoped. Never use ``.all()`` on tenant models.

5. **Deployment Modes**: Environment variable ``DEPLOYMENT_MODE`` switches between shared SaaS (multiple orgs) and dedicated (single org) deployments.

6. **Domain Events**: Publish ``OrganizationCreatedEvent``, ``UserJoinedOrganizationEvent`` to decouple organization lifecycle from other modules.

7. **Test Isolation**: Write explicit tests verifying that data from one organization is never visible to another.

8. **Defense in Depth**: Combine queryset filtering with object-level permission checks, especially for update and delete operations.
