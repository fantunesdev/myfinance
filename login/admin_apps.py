from django.contrib.admin.apps import AdminConfig


class SecurityAdminConfig(AdminConfig):
    default_site = 'login.admin_site.SecurityAdminSite'
