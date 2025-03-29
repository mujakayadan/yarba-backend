"""Prompt template for publications."""

from .base import BasePrompt

TEMPLATE = """Task: Based on the provided job description and candidate's research work, create a concise publications section.

Instructions:
- Include maximum ${publications_details_max_publications} publications
- Prioritize publications that are:
  1. Most relevant to the target position and industry
  2. Most recent and impactful
  3. Published in well-recognized journals or conferences
  4. Demonstrate technical expertise in relevant areas
- Format publication dates consistently (MM/YYYY)
- Include links to the publications where available
- Order publications by relevance to the job description, then by recency
- Focus on publications that showcase skills and knowledge applicable to the position

Output Format:
Your response should be structured as a valid JSON object matching the PublicationsListSchema format.
The structure should be:
```json
{
  "publications": [
    {
      "name": "Publication Title",
      "publisher": "Journal/Conference Name",
      "link": "https://doi.org/publication-link",
      "time": "MM/YYYY"
    },
    ...more publications...
  ]
}
```

Example:
{
  "publications": [
    {
      "name": "High Accuracy Gender Determination Using the Egg Shape Index",
      "publisher": "Nature - Scientific Reports",
      "link": "https://www.nature.com/articles/s41598-023-27772-4",
      "time": "01/2023"
    },
    {
      "name": "Deep Learning for Image Classification: A Comprehensive Review",
      "publisher": "IEEE Transactions on Pattern Analysis and Machine Intelligence",
      "link": "https://ieeexplore.ieee.org/example-link",
      "time": "06/2022"
    }
  ]
}"""


class PublicationsPrompt(BasePrompt):
    """Publications prompt template."""

    def __init__(self):
        """Initialize the publications prompt template."""
        super().__init__(TEMPLATE)


PUBLICATIONS_PROMPT = PublicationsPrompt()
