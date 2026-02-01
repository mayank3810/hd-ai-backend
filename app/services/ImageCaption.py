from app.models.ImageCaption import ImageCaptionModel
from app.models.CompetitorComparison import CompetitorComparisonModel
from datetime import datetime
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from pydantic import BaseModel, Field
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()


class ImageCaptionGenerator(BaseModel):
    caption: str = Field(..., description="Engaging Caption for image in maximum 15 words without any hashtags.") 
class ImageCaptionService:
    def __init__(self):
        self.image_caption_model = ImageCaptionModel()
        self.competitor_comparison_model = CompetitorComparisonModel()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # self.image_analysis = ImageAnalysisHelper()

    async def generate_image_caption_with_llm(self, image_url: str) -> Optional[Dict[str, Any]]:
        """
        Generate an engaging caption for a hotel property image using OpenAI LLM.

        Args:
            image_url: URL of the hotel image

        Returns:
            Dictionary with LLM-generated caption or None if failed
        """
        if not image_url:
            self.logger.warning("No image URL provided")
            return None

        try:
            # # Download image and convert to base64
            # image_bytes = self.download_image_with_retry(image_url)
            # if not image_bytes:
            #     self.logger.error(f"Failed to download image from {image_url}")
            #     return None
            
            # # Convert to base64
            # import base64
            # image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # # Determine content type
            # if image_url.lower().endswith(('.png')):
            #     content_type = 'image/png'
            # elif image_url.lower().endswith(('.gif')):
            #     content_type = 'image/gif'
            # elif image_url.lower().endswith(('.webp')):
            #     content_type = 'image/webp'
            # else:
            #     content_type = 'image/jpeg'
            
            # base64_data_url = f"data:{content_type};base64,{image_base64}"

            # Build messages payload
            messages = [
                {
                    "role": "system",
                    "content": "You are a creative copywriter specialized in hotel marketing. "
                               "Generate an engaging, appealing caption for hotel property images. "
                               "Return ONLY JSON in the format: {\"caption\": \"...\"}."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Create an engaging caption in max 15 words for this hotel property image."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        }
                    ]
                }
            ]

            # Call OpenAI vision API with structured output
            completion = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=messages,
                response_format=ImageCaptionGenerator,
            )

            # Extract parsed result
            result = completion.choices[0].message.parsed.model_dump()

            # Add metadata
            caption_data = {
                **result
            }

            return caption_data

        except Exception as e:
            logging.error(f"Error getting or generating image caption: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_or_generate_caption(self, image_url: str) -> dict:
        """
        Get image caption by URL, if not found generate using ImageAnalysis helper
        """
        try:
            # Check if caption already exists
            existing_caption = await self.image_caption_model.get_image_caption_by_url(image_url)
            
            if existing_caption:
                return {
                    "success": True,
                    "data": {
                        "imageUrl": image_url,
                        "caption": existing_caption.caption,
                        "isGenerated": False
                    }
                }
            
            # Generate new caption using ImageAnalysis helper
            generated_caption_result = await self.generate_image_caption_with_llm(image_url)
            
            if not generated_caption_result:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to generate caption for the image"
                }
            
            generated_caption = generated_caption_result["caption"]
            
            if not generated_caption:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to generate caption for the image"
                }
            
            # Save the generated caption
            caption_data = {
                "imageUrl": image_url,
                "caption": generated_caption,
                "createdAt": datetime.utcnow()
            }
            
            await self.image_caption_model.upsert_image_caption(image_url, caption_data)
            
            return {
                "success": True,
                "data": {
                    "imageUrl": image_url,
                    "caption": generated_caption,
                    "isGenerated": True
                }
            }

        except Exception as e:
            logging.error(f"Error getting or generating image caption: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_bulk_captions(self, image_urls: list) -> dict:
        """
        Get captions for multiple image URLs from the database
        """
        try:
            if not image_urls or not isinstance(image_urls, list):
                return {
                    "success": False,
                    "data": None,
                    "error": "Image URLs must be provided as a non-empty list"
                }

            # Get existing captions from database
            existing_captions = await self.image_caption_model.get_image_captions_by_urls(image_urls)
            
            return {
                "success": True,
                "data": existing_captions
            }

        except Exception as e:
            logging.error(f"Error getting bulk image captions: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_image_captions_by_source(self, operator_id: str, property_id: str, source: str) -> dict:
        """
        Return list of { imageId, url } for the given operator, property and source
        """
        try:
            valid_sources = ["airbnb", "booking", "vrbo"]
            if source.lower() not in valid_sources:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Invalid source. Must be one of: {', '.join(valid_sources)}"
                }

            comparison = await self.competitor_comparison_model.get_competitor_comparison_by_operator_and_property_id(
                operator_id=operator_id,
                property_id=property_id
            )

            if not comparison:
                return {"success": True, "data": []}

            field_name = f"imageCaptions{source.capitalize()}"
            items = getattr(comparison, field_name, [])

            # items are of ImageCaption pydantic model or dicts
            response_items = []
            for item in items:
                # Pydantic model access vs dict access
                image_id = getattr(item, "imageId", None) if hasattr(item, "imageId") else item.get("imageId")
                url = getattr(item, "url", None) if hasattr(item, "url") else item.get("url")
                caption = getattr(item, "caption", None) if hasattr(item, "caption") else item.get("caption")
                if image_id and url:
                    response_items.append({"imageId": image_id, "url": url, "caption": caption})

            return {"success": True, "data": response_items}
        except Exception as e:
            logging.error(f"Error fetching image captions by source: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_or_generate_caption_for_competitor(self, operator_id: str, property_id: str, source: str, image_url: str, image_id: str) -> dict:
        """
        Get or generate image caption for competitor comparison
        Check if caption already exists in CompetitorComparison, if not generate and save
        """
        try:
            # Validate source
            valid_sources = ["airbnb", "booking", "vrbo"]
            if source.lower() not in valid_sources:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Invalid source. Must be one of: {', '.join(valid_sources)}"
                }
            
            # Check if caption already exists in CompetitorComparison
            existing_comparison = await self.competitor_comparison_model.get_competitor_comparison_by_operator_and_property_id(
                operator_id, property_id
            )
            
            if existing_comparison:
                # Check if image caption already exists
                field_name = f"imageCaptions{source.capitalize()}"
                existing_captions = getattr(existing_comparison, field_name, [])
                
                for caption in existing_captions:
                    if caption.imageId == image_id:
                        return {
                            "success": True,
                            "data": {
                                "imageUrl": image_url,
                                "imageId": image_id,
                                "caption": caption.caption,
                                "isGenerated": False,
                                "generatedAt": caption.generatedAt
                            }
                        }
            
            # Generate new caption using LLM
            generated_caption_result = await self.generate_image_caption_with_llm(image_url)
            
            if not generated_caption_result:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to generate caption for the image"
                }
            
            generated_caption = generated_caption_result["caption"]
            
            if not generated_caption:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to generate caption for the image"
                }
            
            # Create image caption data
            image_caption_data = {
                "url": image_url,
                "imageId": image_id,
                "caption": generated_caption,
                "generatedAt": datetime.utcnow()
            }
            
            # Save to CompetitorComparison
            success = await self.competitor_comparison_model.add_image_caption(
                operator_id=operator_id,
                property_id=property_id,
                source=source.lower(),
                image_caption=image_caption_data
            )
            
            if not success:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to save image caption to competitor comparison"
                }
            
            return {
                "success": True,
                "data": {
                    "imageUrl": image_url,
                    "imageId": image_id,
                    "caption": generated_caption,
                    "isGenerated": True,
                    "generatedAt": image_caption_data["generatedAt"]
                }
            }

        except Exception as e:
            logging.error(f"Error getting or generating image caption for competitor: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
