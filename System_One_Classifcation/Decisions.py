import argparse
import base64
import mimetypes
from io import BytesIO
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageOps

def main():
   parser = argparse.ArgumentParser(description="Ask a yes/no question about an image.")
   parser.add_argument("filename", help="Filename inside Image_Files, e.g. photo.jpg")
   parser.add_argument("question", nargs="?", default="Does this image contain a person?")
   args = parser.parse_args()

   folder = Path(__file__).resolve().parent
   image_folder = folder / "Image_Files"
   image_path = (image_folder / args.filename).resolve()
   if not image_path.is_relative_to(image_folder) or not image_path.is_file():
       parser.error("Choose an existing file inside Image_Files.")
   mime_type = mimetypes.guess_type(image_path.name)[0]
   if mime_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
       parser.error("Use a JPEG, PNG, WebP, or non-animated GIF image.")

   load_dotenv(folder / ".env")
   with Image.open(image_path) as image:
       if image.format == "MPO":
           # Multi-picture JPEG photos can include auxiliary frames.
           image.seek(0)
       elif getattr(image, "is_animated", False):
           parser.error("Use a non-animated image.")
       # Apply camera orientation metadata to the pixels before uploading.
       corrected = ImageOps.exif_transpose(image)
       buffer = BytesIO()
       corrected.convert("RGBA" if "A" in corrected.getbands() else "RGB").save(
           buffer, format="PNG"
       )
   mime_type = "image/png"
   encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
   decision = OpenAI().decisions.create(
       model="gpt-6-luna",
       input=[{
           "role": "user",
           "content": [{
               "type": "input_image",
               "image_url": f"data:{mime_type};base64,{encoded}",
           }],
       }],
       questions=[{
           "type": "predicate",
           "name": "image_question",
           "instructions": args.question,
       }],
   )
   print(decision.model_dump_json(indent=2))
   usage = decision.usage
   print("\nToken usage for this API call:")
   print(f"  Input:  {usage.input_tokens:,}")
   print(f"  Total:  {usage.total_tokens:,}")

if __name__ == "__main__":
   main()

