#!/usr/bin/env python
"""
A simple script to test the job extraction endpoint.
"""
import asyncio
import json

import aiohttp


async def test_job_extraction():
    base_url = "http://localhost:8000/api/v1/jobs/extract/"
    # Use the Lensa URL that worked with GenericExtractor in debug script
    test_job_url = "https://www.linkedin.com/jobs/view/4231948770/?refId=Zr0wg3bpSKSpMxzgDuMmWw%3D%3D&trackingId=h1tHDf%2F0Ti6pQvcqRdhf%2BQ%3D%3D"

    # The URL needs to be passed as a query parameter, not in the body
    url = f"{base_url}?url={test_job_url}"

    async with aiohttp.ClientSession() as session:
        print(f"Testing job extraction with URL: {test_job_url}")
        async with session.post(url) as response:
            print(f"Status: {response.status}")

            if response.status == 200:
                data = await response.json()
                print("Success! Job details extracted:")
                print(json.dumps(data, indent=2))
            else:
                print(f"Error: {await response.text()}")


if __name__ == "__main__":
    asyncio.run(test_job_extraction())
