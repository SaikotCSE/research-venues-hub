from django.forms.renderers import TemplatesSetting


class FormRenderer(TemplatesSetting):
    """Render every Django form with the project's accessible, Tailwind-styled templates."""

    form_template_name = "forms/form.html"
    field_template_name = "forms/field.html"
