"""Adapter for Ashby hosted job applications."""

from __future__ import annotations

from typing import Any

from selenium.webdriver.common.by import By

from job_automation.adapters.base import ApplicationAdapter


class AshbyAdapter(ApplicationAdapter):
    """Recognise Ashby's dynamic labels and common application fields."""

    name = "ashby"

    def matches(self, url: str) -> bool:
        return "ashbyhq.com" in url.casefold()

    def identity(self, driver: Any, control: Any, fallback: str) -> str:
        """Ashby commonly nests a label beside a field without ``for``."""
        control_id = control.get_attribute("id") or ""
        if control_id:
            for selector in (
                f"label[for='{control_id}']",
                "xpath=ancestor::*[self::div or self::fieldset][.//label][1]//label[1]",
            ):
                try:
                    if selector.startswith("xpath="):
                        label = control.find_element(By.XPATH, selector.removeprefix("xpath="))
                    else:
                        label = driver.find_element(By.CSS_SELECTOR, selector)
                    text = label.text.strip()
                    if text:
                        return f"{text} {fallback}".strip()
                except Exception:
                    continue
        return fallback

    def prepare_values(self, values: dict[str, str]) -> dict[str, str]:
        prepared = dict(values)
        city = prepared.get("city")
        state = prepared.get("state")
        if city and state:
            prepared.setdefault("currentlocation", f"{city}, {state}")
            prepared.setdefault("cityandprovincestate", f"{city}, {state}")
        # Ashby uses these stable system field identifiers on many forms.
        aliases = {
            "_systemfieldname": "name",
            "_systemfieldemail": "email",
            "linkedin": "linkedin",
            "currentcompany": "company",
        }
        for destination, source in aliases.items():
            if source in prepared:
                prepared.setdefault(destination, prepared[source])
        return prepared
