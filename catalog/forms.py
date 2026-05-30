from django import forms

from catalog.models import Product


class ProductAdminForm(forms.ModelForm):
    stock_lines = forms.CharField(
        label="Add stock in bulk",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 10,
                "placeholder": "email1@example.com:password1\nemail2@example.com:password2",
            }
        ),
        help_text="Optional. Paste one stock item per line. Blank lines are ignored and secrets are encrypted.",
    )
    notify_users_about_stock = forms.BooleanField(
        label="Notify users if stock is added",
        required=False,
        initial=False,
        help_text="Sends the restock message only when the bulk stock box has stock lines.",
    )

    class Meta:
        model = Product
        fields = "__all__"


class BulkStockUploadForm(forms.Form):
    notify_users = forms.BooleanField(
        label="Notify users about this stock update",
        required=False,
        initial=True,
    )
    stock_lines = forms.CharField(
        label="Stock lines",
        widget=forms.Textarea(
            attrs={
                "rows": 16,
                "placeholder": "email1@example.com:password1\nemail2@example.com:password2",
            }
        ),
        help_text="One stock item per line. Blank lines are ignored.",
    )
