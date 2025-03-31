# For this website 

{{url}}

Write a scraper to capture all the data on this page into this schema format 

```py
{% if not schema %}
{{ raise("Schema content is required but was undefined or empty") }}
{% else %}
{{ schema }}
{% endif %}
```

