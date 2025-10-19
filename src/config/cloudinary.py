# import os
# import cloudinary
# import cloudinary.uploader
# import cloudinary.api
# from cloudinary.utils import cloudinary_url
# from typing import Dict, Any, Optional, Union, List, Tuple
# import os


# # Configuration
# def configure_cloudinary() -> None:
#     """Configure Cloudinary with credentials from environment variables or directly."""
#     cloudinary.config(
#         cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
#         api_key=os.getenv("CLOUDINARY_API_KEY"),
#         api_secret=os.getenv("CLOUDINARY_API_SECRET"),
#         secure=True,
#     )


# # Initialize configuration
# configure_cloudinary()


# def upload_image(file_path: str, **options) -> Dict[str, Any]:
#     """Upload an image to Cloudinary and return the result.

#     Args:
#         file_path: Local path to the image file or URL of an image
#         **options: Additional options for the upload
#             - public_id: Custom public ID for the image
#             - folder: Folder in Cloudinary to store the image
#             - resource_type: Type of resource ('image', 'video', 'raw', etc.)
#             - tags: List of tags to assign to the image
#             - transformation: Transformation to apply during upload
#             - format: Format to convert the image to
#             - overwrite: Whether to overwrite existing images with the same public_id

#     Returns:
#         Dictionary containing upload result with keys like 'public_id', 'secure_url', etc.
#     """
#     # Set default options if not provided
#     if "resource_type" not in options:
#         options["resource_type"] = "image"

#     # Upload the image
#     result = cloudinary.uploader.upload(file_path, **options)
#     return result


# def delete_image(public_id: str, **options) -> Dict[str, Any]:
#     """Delete an image from Cloudinary.

#     Args:
#         public_id: Public ID of the image to delete
#         **options: Additional options for deletion
#             - resource_type: Type of resource ('image', 'video', 'raw', etc.)
#             - invalidate: Whether to invalidate CDN cache

#     Returns:
#         Dictionary containing the deletion result
#     """
#     # Set default options if not provided
#     if "resource_type" not in options:
#         options["resource_type"] = "image"

#     # Delete the image
#     result = cloudinary.uploader.destroy(public_id, **options)
#     return result


# def update_image(public_id: str, file_path: str, **options) -> Dict[str, Any]:
#     """Update an existing image by uploading a new one with the same public_id.

#     Args:
#         public_id: Public ID of the image to update
#         file_path: Local path to the new image file or URL of an image
#         **options: Additional options for the upload

#     Returns:
#         Dictionary containing upload result
#     """
#     # Ensure we're overwriting the existing image
#     options["public_id"] = public_id
#     options["overwrite"] = True

#     # Upload the new image with the same public_id
#     result = upload_image(file_path, **options)
#     return result


# def get_image_url(public_id: str, **options) -> str:
#     """Generate a URL for an image with optional transformations.

#     Args:
#         public_id: Public ID of the image
#         **options: Transformation options
#             - width: Width to resize to
#             - height: Height to resize to
#             - crop: Cropping method ('fill', 'fit', 'limit', 'thumb', 'crop', etc.)
#             - fetch_format: Format to deliver the image in ('auto', 'jpg', 'png', etc.)
#             - quality: Quality of the image ('auto', or 1-100)
#             - effect: Effects to apply
#             - gravity: How to position the image ('auto', 'face', 'center', etc.)

#     Returns:
#         URL string for the transformed image
#     """
#     url, _ = cloudinary_url(public_id, **options)
#     return url


# def list_images(prefix: Optional[str] = None, **options) -> Dict[str, Any]:
#     """List images in your Cloudinary account.

#     Args:
#         prefix: Filter images by prefix
#         **options: Additional options for listing
#             - type: Resource type ('upload', 'private', etc.)
#             - max_results: Maximum number of results to return
#             - next_cursor: For pagination
#             - tags: Filter by tags

#     Returns:
#         Dictionary containing the list of images
#     """
#     if prefix:
#         options["prefix"] = prefix

#     result = cloudinary.api.resources(**options)
#     return result
