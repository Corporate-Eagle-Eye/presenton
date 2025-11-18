import aiohttp
import os
from fastapi import HTTPException
from models.presentation_layout import PresentationLayoutModel
from typing import List

async def get_layout_by_name(layout_name: str) -> PresentationLayoutModel:
    # Use environment variable or default to localhost:3000 for dev
    nextjs_url = os.getenv("NEXTJS_URL", "http://localhost:3000")
    url = f"{nextjs_url}/api/template?group={layout_name}"
    
    # Puppeteer can take 1-2 minutes to launch and scrape, match Next.js timeout
    timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            if response.status != 200:
                error_text = await response.text()
                raise HTTPException(
                    status_code=404,
                    detail=f"Template '{layout_name}' not found: {error_text}"
                )
            layout_json = await response.json()
    # Parse the JSON into your Pydantic model
    return PresentationLayoutModel(**layout_json)
