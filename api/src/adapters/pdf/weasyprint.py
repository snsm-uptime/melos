"""PDF rendering using WeasyPrint"""
from typing import List, Dict, Any
from weasyprint import HTML, CSS
from jinja2 import Template
from io import BytesIO
from api.src.application.ports import PdfRenderer


SHOPPING_LIST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; color: #333; }
        .container { max-width: 800px; margin: 40px auto; padding: 20px; }
        .header { margin-bottom: 30px; }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header p { color: #666; font-size: 12px; }
        .section { margin-bottom: 25px; }
        .section h2 {
            font-size: 16px;
            background-color: #f5f5f5;
            padding: 8px 12px;
            margin-bottom: 12px;
            border-left: 4px solid #2196F3;
        }
        .item {
            padding: 8px 12px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .quantity { font-weight: bold; min-width: 120px; }
        .warning {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 8px 12px;
            margin-bottom: 5px;
            border-radius: 4px;
            font-size: 12px;
            color: #856404;
        }
        .meta {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 11px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Shopping List</h1>
            <p><strong>Kitchen:</strong> {{ kitchen_name }}</p>
            <p><strong>Generated:</strong> {{ generated_date }}</p>
            <p><strong>Serving:</strong> {{ headcount }} people</p>
        </div>

        {% for category, items in items_by_category.items() %}
        <div class="section">
            <h2>{{ category }}</h2>
            {% for item in items %}
            <div class="item">
                <div>{{ item.name }}</div>
                <div class="quantity">{{ item.quantity | round(2) }} {{ item.unit }}</div>
            </div>
            {% if item.is_linear == False %}
            <div class="warning">⚠ Please review this item</div>
            {% endif %}
            {% endfor %}
        </div>
        {% endfor %}

        <div class="meta">
            <p>This list was automatically generated from your recipes.</p>
        </div>
    </div>
</body>
</html>
"""


class WeasyPrintRenderer(PdfRenderer):
    """Render shopping lists to PDF using WeasyPrint"""

    async def render_shopping_list(
        self,
        kitchen_name: str,
        headcount: int,
        items: List[Dict[str, Any]],
        generated_date: str
    ) -> bytes:
        """
        Render shopping list to PDF
        Items format: [{"name": "...", "quantity": 2.5, "unit": "cup", "is_linear": True}, ...]
        """
        # Group items by category
        items_by_category = self._group_items_by_category(items)

        # Render template
        template = Template(SHOPPING_LIST_TEMPLATE)
        html_string = template.render(
            kitchen_name=kitchen_name,
            headcount=headcount,
            items_by_category=items_by_category,
            generated_date=generated_date
        )

        # Convert to PDF
        pdf_bytes = HTML(string=html_string).write_pdf()
        return pdf_bytes

    @staticmethod
    def _group_items_by_category(items: List[Dict]) -> Dict[str, List[Dict]]:
        """Group items by category for display"""
        grouped = {}
        for item in items:
            category = item.get("category", "Other")
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(item)

        return grouped
