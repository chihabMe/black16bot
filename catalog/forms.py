from django import forms


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
