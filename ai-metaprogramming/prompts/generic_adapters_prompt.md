Take these following pydantic python objects

```py
{% if not schemas %}
{{ raise("Scrapers content is required but was undefined or empty") }}
{% else %}
{{ schemas }}
{% endif %}
```

And write adapter functions that convert each of them into one of the appropriate generic types.
