"""Research companies for personalized cover letters."""

from __future__ import annotations

from anthropic import Anthropic


class CompanyResearcher:
    """Research companies to personalize cover letters."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize researcher."""
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()

    def research_company(self, company_name: str, industry: str = "") -> dict[str, str]:
        """Research a company for cover letter personalization.

        Args:
            company_name: Name of the company
            industry: Optional industry

        Returns:
            Dictionary with company info
        """
        prompt = f"""Research and provide key information about {company_name}:

Provide concise information about:
1. Company mission/values
2. Recent achievements or news
3. Company culture highlights
4. Key products/services
5. Why someone would want to work there

Keep it brief (2-3 sentences per point) and suitable for cover letter references."""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )

        return {"company": company_name, "research": response.content[0].text}

    def get_company_talking_points(self, company_name: str) -> list[str]:
        """Get specific talking points about a company.

        Args:
            company_name: Name of the company

        Returns:
            List of talking points
        """
        prompt = f"""Generate 5 specific, compelling talking points about {company_name} that would be good to mention in a cover letter.

Focus on:
- Company achievements
- Innovation/technology
- Company culture
- Impact on industry
- Growth opportunities

Return as a numbered list."""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return lines[:5]
