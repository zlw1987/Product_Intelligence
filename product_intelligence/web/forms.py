"""The standalone intake form (PRODUCT-INTEL.1B).

One job: take two raw strings off an HTML form and produce the canonical
`ResearchRequest`, or an error a person can read.

Why this form validates almost nothing
--------------------------------------

`ResearchRequest` is the single authority on what valid intake is: it strips
surrounding whitespace, refuses a pair that is empty on both sides, and never
rewrites the interior of a value. Restating any of that here would create a
second, subtly different policy — and the two would drift, because nothing
would fail when they did. So both fields are individually optional at the field
level, and the "at least one of them" rule is enforced by *constructing the
contract* and reporting what it says.

That is also why both fields set ``strip=False``. Django's `CharField` strips
by default, which happens to agree with the contract today; leaving it on would
mean the form quietly owns a normalization rule that belongs to the domain, and
a later change to either side would be invisible until the persisted values
disagreed. The form hands over exactly what the browser sent and reads back
whatever the contract made of it.

Nothing here normalizes a part number — not case, not punctuation, not hyphens,
not interior whitespace. Part-number normalization is a deterministic identity
concern (2A/3C), and inventing a version of it at the transport boundary would
put a matching decision in the one layer forbidden to make one.
"""

from __future__ import annotations

from django import forms

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.errors import DomainValidationError


class ResearchRequestForm(forms.Form):
    """Collects an MPN and a description and yields a `ResearchRequest`."""

    manufacturer_part_number = forms.CharField(
        label="Manufacturer part number",
        required=False,
        strip=False,
        widget=forms.TextInput(attrs={"autofocus": "autofocus", "autocomplete": "off"}),
        help_text="The part number as printed. Enter it exactly; nothing is "
        "reformatted.",
    )
    description = forms.CharField(
        label="Product description",
        required=False,
        strip=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Free text. Either field may be left blank, but not both.",
    )

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._research_request: ResearchRequest | None = None

    def clean(self) -> dict[str, object]:
        cleaned_data = super().clean()

        try:
            self._research_request = ResearchRequest(
                manufacturer_part_number=cleaned_data.get(
                    "manufacturer_part_number", ""
                ),
                description=cleaned_data.get("description", ""),
            )
        except DomainValidationError as error:
            # Translation, not re-implementation: the contract decided this was
            # invalid, and the form's only contribution is showing the reason on
            # the page instead of raising a 500.
            raise forms.ValidationError(str(error)) from error

        return cleaned_data

    @property
    def research_request(self) -> ResearchRequest:
        """The canonical request this submission produced.

        Available only after `is_valid()` has returned True — a form that did
        not validate produced no request, and returning a partially-built one
        would be exactly the fabricated certainty the project forbids.
        """
        if self._research_request is None:
            raise ValueError(
                "no canonical research request exists; the form has not been "
                "validated, or validation failed"
            )
        return self._research_request
