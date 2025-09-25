# main_app.py
import streamlit as st
import base64
from PIL import Image
from io import BytesIO
from typing import List, Optional, Type
import os
from dotenv import load_dotenv

# --- Core Dependencies ---
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers.json import JsonOutputParser

# --- Load Environment Variables ---
load_dotenv()

# --- ADDED FOR AUTHENTICATION ---
def check_password():
    """Returns `True` if the user had the correct password."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    st.header("🔐 Secure Access")
    password = st.text_input("Enter the password to access the app", type="password")
    if st.button("Login"):
        correct_password = os.getenv("APP_PASSWORD")
        if password == correct_password:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 Incorrect password. Please try again.")
    return False

if not check_password():
    st.stop()
# ------------------------------------

# --- Page & Session State Configuration ---
st.set_page_config(
    page_title="AI Social Content Generator 📱✨",
    page_icon="🚀",
    layout="wide",
)

# Initialize session state
if "generated_content" not in st.session_state:
    st.session_state.generated_content = {}
if "image_base64" not in st.session_state:
    st.session_state.image_base64 = None
if "platforms_selected" not in st.session_state:
    st.session_state.platforms_selected = []
if "business_context" not in st.session_state:
    st.session_state.business_context = ""
if "last_uploaded_filename" not in st.session_state:
    st.session_state.last_uploaded_filename = None
if "just_generated" not in st.session_state:
    st.session_state.just_generated = False
# --- NEW: Session state for the PIL image object ---
if "pil_image" not in st.session_state:
    st.session_state.pil_image = None

# --- Pydantic Models for Structured Output ---
class InstagramContent(BaseModel):
    caption: str = Field(description="Engaging Instagram caption (max 2,200 chars), use emojis.")
    hashtags: List[str] = Field(description="List of 15-20 relevant hashtags, each starting with '#'.")
    alt_text: str = Field(description="Descriptive alt text for accessibility (max 125 chars).")

class FacebookContent(BaseModel):
    post_text: str = Field(description="Compelling Facebook post text, can be longer and more detailed. Use emojis and ask a question to encourage engagement.")
    headline: Optional[str] = Field(description="An optional catchy headline if the post is promotional.")

class XContent(BaseModel):
    tweet: str = Field(description="Concise and impactful tweet (max 280 chars). Use emojis and 2-3 key hashtags.")
    hashtags: List[str] = Field(description="A list of 2-3 relevant hashtags for the tweet, each starting with '#'.")

class PinterestContent(BaseModel):
    title: str = Field(description="SEO-friendly Pinterest pin title (max 100 chars).")
    description: str = Field(description="Detailed description with keywords (max 500 chars).")
    keywords: List[str] = Field(description="List of 10-15 keywords, without '#'.")

class LinkedInContent(BaseModel):
    post_text: str = Field(description="Professional and insightful LinkedIn post. Share expertise or company news. Use 3-5 professional hashtags.")
    hashtags: List[str] = Field(description="List of 3-5 professional hashtags, each starting with '#'.")

# --- Platform Configuration ---
PLATFORM_CONFIG = {
    "instagram": {"name": "Instagram", "icon": "📷", "pydantic_model": InstagramContent, "prompt": "Generate an engaging caption, 15-20 relevant hashtags, and descriptive alt text for an Instagram post."},
    "facebook": {"name": "Facebook", "icon": "📘", "pydantic_model": FacebookContent, "prompt": "Create a compelling Facebook post with an optional headline. The tone can be more detailed and community-focused. Ask a question to drive comments."},
    "x": {"name": "X (Twitter)", "icon": "🐦", "pydantic_model": XContent, "prompt": "Write a short, punchy tweet (under 280 characters) with 2-3 key hashtags."},
    "pinterest": {"name": "Pinterest", "icon": "📌", "pydantic_model": PinterestContent, "prompt": "Create a keyword-rich title and description for a Pinterest pin. Also provide a list of 10-15 relevant keywords."},
    "linkedin": {"name": "LinkedIn", "icon": "💼", "pydantic_model": LinkedInContent, "prompt": "Compose a professional LinkedIn post. The tone should be informative, industry-relevant, or share company insights. Include 3-5 professional hashtags."}
}

# --- Core Generation Function ---
def generate_for_platform(platform_key: str, image_base64: str, business_context: str, pydantic_model: Type[BaseModel]):
    config = PLATFORM_CONFIG[platform_key]
    parser = JsonOutputParser(pydantic_object=pydantic_model)
    prompt_text = f"""
    You are an expert social media manager. Your task is to create content for {config['name']} based on the provided image and business context.
    **Business Context:**
    {business_context if business_context else "Not provided. Analyze the image for general appeal."}
    **Platform Instructions ({config['name']}):**
    {config['prompt']}
    **Output Format:**
    You MUST provide your response in a valid JSON object that strictly follows this schema. Do not add any text before or after the JSON.
    Schema:
    {parser.get_format_instructions()}
    """
    try:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")
        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7, google_api_key=google_api_key)
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_base64}"}
            ]
        )
        response = model.invoke([message])
        parsed_content = parser.parse(response.content)
        return parsed_content
    except Exception as e:
        st.error(f"Error generating content for {config['name']}: {e}")
        return None

# --- UI Layout ---
st.title("🚀 AI Social Media Content Generator")
st.markdown("Upload an image, describe your business (optional), select your social platforms, and let AI do the rest!")

col1, col2 = st.columns([2, 3])

# --- Column 1: Inputs ---
with col1:
    st.subheader("1. Upload Your Image")
    uploaded_file = st.file_uploader(
        "Click to upload...",
        type=["jpg", "jpeg", "png"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        if st.session_state.last_uploaded_filename != uploaded_file.name:
            st.session_state.generated_content = {}
            st.session_state.last_uploaded_filename = uploaded_file.name
        
        # Process and store the image
        img = Image.open(uploaded_file)
        st.session_state.pil_image = img  # Store PIL image in session state
        
        buffered = BytesIO()
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(buffered, format="JPEG")
        st.session_state.image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    st.subheader("2. Describe Your Work (Optional)")
    st.session_state.business_context = st.text_area(
        "Describe Your Work (Optional)",
        value=st.session_state.business_context,
        placeholder="e.g., I run an online academy teaching Quran to children.",
        help="Providing context helps the AI generate more relevant posts!",
        label_visibility="collapsed"
    )

# --- Column 2: Preview and Actions ---
with col2:
    st.subheader("Image Preview")
    if st.session_state.pil_image:
        st.image(
            st.session_state.pil_image,
            caption="Your uploaded image",
            use_container_width=True
        )
    else:
        st.info("Your uploaded image will be shown here.")
    
    st.markdown("---")
    st.subheader("3. Select Platforms")
    
    selected_platforms = []
    num_columns = 5
    icon_cols = st.columns(num_columns)
    
    for i, (key, config) in enumerate(PLATFORM_CONFIG.items()):
        with icon_cols[i % num_columns]:
            if st.checkbox(f"{config['icon']} {config['name']}", key=f"cb_{key}", value=(key in st.session_state.platforms_selected)):
                selected_platforms.append(key)

    st.session_state.platforms_selected = selected_platforms
    
    st.markdown("---")
    
    can_generate = st.session_state.image_base64 and st.session_state.platforms_selected
    
    if st.button("✨ Generate Content", type="primary", use_container_width=True, disabled=not can_generate):
        with st.status("Generating content...", expanded=True) as status:
            st.session_state.generated_content = {}
            for platform_key in st.session_state.platforms_selected:
                platform_name = PLATFORM_CONFIG[platform_key]['name']
                status.update(label=f"✍️ Crafting post for {platform_name}...")
                content = generate_for_platform(
                    platform_key,
                    st.session_state.image_base64,
                    st.session_state.business_context,
                    PLATFORM_CONFIG[platform_key]['pydantic_model']
                )
                if content:
                    st.session_state.generated_content[platform_key] = content
            
            if st.session_state.generated_content:
                st.session_state.just_generated = True

            status.update(label="✅ All content generated!", state="complete")

# --- Display Generated Content (Full Width) ---
if st.session_state.generated_content:
    st.markdown("<div id='output-anchor'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("🎉 Your Generated Content")
    
    platform_keys_with_content = [
        key for key in st.session_state.platforms_selected 
        if key in st.session_state.generated_content
    ]
    
    tabs = st.tabs([PLATFORM_CONFIG[key]['name'] for key in platform_keys_with_content])

    for i, tab in enumerate(tabs):
        platform_key = platform_keys_with_content[i]
        content_data = st.session_state.generated_content[platform_key]
        
        with tab:
            if platform_key == 'instagram':
                st.subheader("Caption")
                full_caption = content_data.get('caption', '')
                hashtags = " ".join(content_data.get('hashtags', []))
                display_caption = f"{full_caption}\n\n.\n.\n.\n\n{hashtags}"
                st.code(display_caption, language=None)
                
                st.subheader("Alt Text")
                alt_text = content_data.get('alt_text', '')
                st.code(alt_text, language=None)
            else:
                for field, value in content_data.items():
                    field_title = field.replace('_', ' ').title()
                    if isinstance(value, list):
                        display_value = " ".join(value) if field == 'hashtags' else ", ".join(value)
                    else:
                        display_value = value if value else ""
                    st.subheader(field_title)
                    st.code(display_value, language=None)

    if st.session_state.get("just_generated", False):
        js_code = """
        <script>
            setTimeout(function() {
                const anchor = document.getElementById('output-anchor');
                if (anchor) {
                    anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 200);
        </script>
        """
        st.components.v1.html(js_code)
        st.session_state.just_generated = False










# import streamlit as st
# import os
# import base64
# import json
# from PIL import Image
# from io import BytesIO
# from typing import TypedDict, List, Dict, Any, Optional
# from dotenv import load_dotenv

# # --- Corrected Imports for Pydantic v2 and a working Streamlit Extras ---
# # NOTE: Ensure you have run 'pip install --upgrade streamlit-extras'
# from pydantic import BaseModel, Field
# from streamlit_extras.copy_to_clipboard import copy_to_clipboard

# from langgraph.graph import StateGraph, END
# from langchain_core.messages import HumanMessage
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_core.output_parsers.json import JsonOutputParser
# from google.api_core.exceptions import ResourceExhausted

# # --- Load Environment Variables ---
# load_dotenv()

# # --- Page Configuration ---
# st.set_page_config(
#     page_title="Pro Social Media Content Generator 📱✨",
#     page_icon="🚀",
#     layout="wide",
# )

# # --- Pydantic Models ---
# class InstagramContent(BaseModel):
#     caption: str = Field(description="Instagram caption (2,200 characters max).")
#     hashtags: List[str] = Field(description="List of 15-30 hashtags, each starting with '#'.")
#     alt_text: str = Field(description="Instagram alt text (100 characters max).")

# class PinterestContent(BaseModel):
#     title: str = Field(description="Pinterest pin title (100 characters max).")
#     description: str = Field(description="Pinterest pin description (500 characters max).")
#     keywords: List[str] = Field(description="List of 15-20 keywords, without '#'.")
#     alt_text: str = Field(description="Pinterest alt text (500 characters max).")

# class SocialMediaContent(BaseModel):
#     instagram: InstagramContent
#     pinterest: PinterestContent

# class ImageAnalysis(BaseModel):
#     content_type: str
#     main_subjects: List[str]
#     style_and_mood: str
#     target_audience: str

# # --- LangGraph State ---
# class GraphState(TypedDict):
#     image_base64: str
#     analysis: Optional[ImageAnalysis]
#     social_content: Optional[SocialMediaContent]
#     validation_feedback: str
#     retry_count: int
#     max_retries: int
#     error_history: List[str]

# # --- Validator ---
# # CORRECTED: This now consistently uses dictionary access ['...']
# def comprehensive_content_validator(content: Dict[str, Any]) -> str:
#     issues = []
#     try:
#         ig = content['instagram']
#         if len(ig['caption']) > 2200: issues.append("Instagram Caption: Exceeds 2,200 characters.")
#         if len(ig['alt_text']) > 100: issues.append("Instagram Alt Text: Exceeds 100 characters.")
#         if not (15 <= len(ig['hashtags']) <= 30): issues.append(f"Instagram Hashtags: Incorrect count ({len(ig['hashtags'])}). Must be 15-30.")
#         if missing := [h for h in ig['hashtags'] if not h.startswith('#')]: issues.append(f"Instagram Hashtags: Missing '#' on: {missing[:3]}")

#         pin = content['pinterest']
#         if len(pin['title']) > 100: issues.append("Pinterest Title: Exceeds 100 characters.")
#         if len(pin['description']) > 500: issues.append("Pinterest Description: Exceeds 500 characters.")
#         if not (15 <= len(pin['keywords']) <= 20): issues.append(f"Pinterest Keywords: Incorrect count ({len(pin['keywords'])}). Must be 15-20.")
#         if has_hash := [k for k in pin['keywords'] if k.startswith('#')]: issues.append(f"Pinterest Keywords: Should not have '#': {has_hash[:3]}")
#     except KeyError as e:
#         issues.append(f"A required field is missing from the AI's response: {e}")

#     return "\n- ".join(["Validation Failed. You MUST fix these issues:"] + issues) if issues else "Validation Passed"

# # --- LangGraph Nodes ---
# def analyze_image_node(state: GraphState):
#     st.write("Step 1: 🧐 Analyzing image...")
#     # CORRECTED: Using the valid model name 'gemini-1.5-flash'
#     model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
#     parser = JsonOutputParser(pydantic_object=ImageAnalysis)
#     prompt = f"Analyze the image for social media. Output JSON only. Schema: {parser.get_format_instructions()}"
#     message = HumanMessage(content=[{"type": "text", "text": prompt}, {"type": "image_url", "image_url": f"data:image/jpeg;base64,{state['image_base64']}"}])
#     try:
#         analysis = (model | parser).invoke([message])
#         return {"analysis": analysis, "retry_count": 0}
#     except Exception as e:
#         return {"error_history": [f"Image Analysis Failed: {e}"]}

# def create_social_content_node(state: GraphState):
#     retry_count = state.get('retry_count', 0)
#     st.write(f"Step 2: ✍️ Crafting content (Attempt #{retry_count + 1})...")
#     analysis = state['analysis']
#     feedback = state.get('validation_feedback', '')

#     prompt = f"""
#     You are an expert social media content creator. Generate perfectly formatted content based on the rules and analysis.

#     <CRITICAL_RULES>
#     Instagram: caption(max 2200), hashtags(15-30, must start with '#'), alt_text(max 100).
#     Pinterest: title(max 100), description(max 500), keywords(15-20, NO '#'), alt_text(max 500).
#     </CRITICAL_RULES>

#     <IMAGE_ANALYSIS>
#     {analysis}
#     </IMAGE_ANALYSIS>

#     {"<PREVIOUS_ATTEMPT_FEEDBACK>" + feedback + "</PREVIOUS_ATTEMPT_FEEDBACK>" if "Failed" in feedback else ""}

#     INSTRUCTIONS: Think step-by-step. Review your drafted content against every rule. Once 100% compliant, format it as a single, valid JSON object and nothing else.
#     """
    
#     # CORRECTED: Using the valid model name 'gemini-1.5-flash'
#     model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)
#     # The parser will output a dict because that's how LangGraph state works best
#     parser = JsonOutputParser()
#     try:
#         content = (model | parser).invoke(prompt)
#         return {"social_content": content}
#     except Exception as e:
#         return {"error_history": [f"Content Generation Failed: {e}"]}

# def validate_content_node(state: GraphState):
#     st.write("Step 3: 🛡️ Validating content...")
#     content = state.get('social_content')
#     if not content:
#         return {"validation_feedback": "Validation Failed: No content was generated."}
    
#     feedback = comprehensive_content_validator(content)
#     return {"validation_feedback": feedback}

# # (The rest of the graph logic remains the same)
# def should_continue(state: GraphState):
#     if state.get("error_history"): return "end"
#     feedback = state.get("validation_feedback", "")
#     if "Failed" in feedback:
#         if state["retry_count"] >= state["max_retries"]:
#             st.warning("⚠️ Max retries reached. Please review the final output carefully.")
#             return "end"
#         else:
#             return "retry"
#     else:
#         st.success("✅ Content generated and validated successfully!")
#         return "end"

# def increment_retry_node(state: GraphState):
#     return {"retry_count": state["retry_count"] + 1}

# workflow = StateGraph(GraphState)
# workflow.add_node("analyzer", analyze_image_node)
# workflow.add_node("content_creator", create_social_content_node)
# workflow.add_node("validator", validate_content_node)
# workflow.add_node("retry_counter", increment_retry_node)
# workflow.set_entry_point("analyzer")
# workflow.add_edge("analyzer", "content_creator")
# workflow.add_edge("content_creator", "validator")
# workflow.add_conditional_edges("validator", should_continue, {"retry": "retry_counter", "end": END})
# workflow.add_edge("retry_counter", "content_creator")
# app = workflow.compile()

# # --- Streamlit UI ---
# st.title("🚀 Pro Social Media Content Generator")
# st.markdown("Upload an image to get validated content for Instagram & Pinterest.")

# uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
# results_container = st.container()

# if uploaded_file:
#     with results_container:
#         st.image(uploaded_file, caption="Uploaded Image", width=350)
    
#     if st.button("✨ Generate Content", type="primary"):
#         with results_container:
#             with st.status("Generating content...", expanded=True) as status:
#                 try:
#                     img = Image.open(uploaded_file)
#                     buffered = BytesIO()
#                     if img.mode == 'RGBA': img = img.convert('RGB')
#                     img.save(buffered, format="JPEG")
#                     img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    
#                     inputs = {"image_base64": img_base64, "max_retries": 2}
#                     final_state = app.invoke(inputs)

#                     content = final_state.get('social_content')
#                     status.update(label="Process complete!", state="complete")
                    
#                     if content:
#                         st.divider()
#                         col1, col2 = st.columns(2)

#                         # CORRECTED: Consistently using dictionary access ['...']
#                         with col1:
#                             st.subheader("📱 Instagram")
#                             ig = content.get('instagram', {})
#                             caption_text = ig.get('caption', '')
#                             st.text_area("Caption", value=caption_text, height=200, key="ig_cap")
#                             if st.button("Copy Caption", key="copy_ig_cap"):
#                                 copy_to_clipboard(caption_text)
#                                 st.success("Caption copied!")
                            
#                             hashtags_text = " ".join(ig.get('hashtags', []))
#                             st.text_area("Hashtags", value=hashtags_text, height=100, key="ig_tags")
#                             if st.button("Copy Hashtags", key="copy_ig_tags"):
#                                 copy_to_clipboard(hashtags_text)
#                                 st.success("Hashtags copied!")
                            
#                             alt_text_ig = ig.get('alt_text', '')
#                             st.text_area("Alt Text", value=alt_text_ig, height=80, key="ig_alt")
#                             if st.button("Copy Alt Text", key="copy_ig_alt"):
#                                 copy_to_clipboard(alt_text_ig)
#                                 st.success("Alt Text copied!")

#                         with col2:
#                             st.subheader("📌 Pinterest")
#                             pin = content.get('pinterest', {})
#                             title_text = pin.get('title', '')
#                             st.text_area("Title", value=title_text, height=60, key="pin_title")
#                             if st.button("Copy Title", key="copy_pin_title"):
#                                 copy_to_clipboard(title_text)
#                                 st.success("Title copied!")
                            
#                             desc_text = pin.get('description', '')
#                             st.text_area("Description", value=desc_text, height=120, key="pin_desc")
#                             if st.button("Copy Description", key="copy_pin_desc"):
#                                 copy_to_clipboard(desc_text)
#                                 st.success("Description copied!")
                            
#                             keywords_text = ", ".join(pin.get('keywords', []))
#                             st.text_area("Keywords", value=keywords_text, height=100, key="pin_kw")
#                             if st.button("Copy Keywords", key="copy_pin_kw"):
#                                 copy_to_clipboard(keywords_text)
#                                 st.success("Keywords copied!")
                            
#                             alt_text_pin = pin.get('alt_text', '')
#                             st.text_area("Alt Text", value=alt_text_pin, height=100, key="pin_alt")
#                             if st.button("Copy Alt Text ", key="copy_pin_alt"):
#                                 copy_to_clipboard(alt_text_pin)
#                                 st.success("Alt Text copied!")
                        
#                         st.components.v1.html("<script>window.scrollTo(0, document.body.scrollHeight);</script>", height=0)
                    
#                     if final_state.get('error_history'):
#                         st.error("An error occurred during the process:")
#                         st.json(final_state['error_history'])

#                 except ResourceExhausted:
#                     st.error("🚦 API Rate Limit Exceeded. Please wait a minute and try again.")
#                 except Exception as e:
#                     st.error(f"A critical application error occurred: {e}")


















# # import streamlit as st
# # import os
# # import base64
# # import json
# # from PIL import Image
# # from io import BytesIO
# # from typing import TypedDict, List, Dict, Any, Optional
# # from dotenv import load_dotenv

# # # --- Corrected Imports for Pydantic v2 and a working Streamlit Extras ---
# # # NOTE: Ensure you have run 'pip install --upgrade streamlit-extras pydantic langchain-google-genai langgraph'
# # from pydantic import BaseModel, Field
# # from streamlit_extras.copy_to_clipboard import copy_to_clipboard

# # from langgraph.graph import StateGraph, END
# # from langchain_core.messages import HumanMessage
# # from langchain_google_genai import ChatGoogleGeneraiAI
# # from langchain_core.output_parsers.json import JsonOutputParser
# # from google.api_core.exceptions import ResourceExhausted

# # # --- Load Environment Variables ---
# # load_dotenv()

# # # --- Page Configuration ---
# # st.set_page_config(
# #     page_title="Pro Social Media Content Generator 📱✨",
# #     page_icon="🚀",
# #     layout="wide",
# # )

# # # --- Pydantic Models (Data Structures) ---
# # class InstagramContent(BaseModel):
# #     caption: str = Field(description="Instagram caption (2,200 characters max).")
# #     hashtags: List[str] = Field(description="List of 15-30 hashtags, each starting with '#'.")
# #     alt_text: str = Field(description="Instagram alt text (100 characters max).")

# # class PinterestContent(BaseModel):
# #     title: str = Field(description="Pinterest pin title (100 characters max).")
# #     description: str = Field(description="Pinterest pin description (500 characters max).")
# #     keywords: List[str] = Field(description="List of 15-20 keywords, without '#'.")
# #     alt_text: str = Field(description="Pinterest alt text (500 characters max).")

# # class SocialMediaContent(BaseModel):
# #     instagram: InstagramContent
# #     pinterest: PinterestContent

# # class ImageAnalysis(BaseModel):
# #     content_type: str
# #     main_subjects: List[str]
# #     style_and_mood: str
# #     target_audience: str

# # # --- Few-Shot Examples for the Prompt ---
# # few_shot_examples = """
# # <EXAMPLE_OF_FAILURE>
# # This is an example of a BAD output that does not follow the rules.
# # {
# #   "instagram": {
# #     "caption": "A very long caption...",
# #     "hashtags": ["travel", "sunset", "#vacation"],
# #     "alt_text": "A beautiful sunset over the ocean with palm trees."
# #   },
# #   "pinterest": {
# #     "title": "A beautiful sunset",
# #     "description": "Just a photo.",
# #     "keywords": ["#travel", "#sunset", "vacation"],
# #     "alt_text": "A scenic view."
# #   }
# # }
# # REASONING FOR FAILURE:
# # - Instagram `hashtags` list only has 3 items (rule is 15-30) and some are missing the '#'.
# # - Pinterest `keywords` list is too short (rule is 15-20) and some incorrectly start with '#'.
# # </EXAMPLE_OF_FAILURE>

# # <EXAMPLE_OF_SUCCESS>
# # This is an example of a GOOD output that follows all rules perfectly.
# # {
# #   "instagram": {
# #     "caption": "Chasing the last light of the day. Every sunset is an opportunity to reset. ✨\\n\\nWhat's your favorite sunset memory?",
# #     "hashtags": ["#sunsetlover", "#oceanview", "#goldenhour", "#travelgram", "#instatravel", "#beachlife", "#paradise", "#naturephotography", "#skyonfire", "#serenity", "#beautifuldestinations", "#wanderlust", "#islandvibes", "#dusk", "#goodvibes", "#travelphotography", "#sunsetphotography"],
# #     "alt_text": "Vibrant orange and pink sunset over a calm ocean with silhouette of palm trees on the right."
# #   },
# #   "pinterest": {
# #     "title": "Breathtaking Ocean Sunset with Palm Tree Silhouettes",
# #     "description": "Discover the magic of golden hour with this stunning sunset photo. Perfect for travel inspiration, wanderlust mood boards, and tropical vacation planning. Save this pin for your future beach getaway ideas and aesthetic travel goals!",
# #     "keywords": ["sunset photography", "ocean wallpaper", "tropical vacation", "beach aesthetic", "travel inspiration", "wanderlust travel", "golden hour light", "palm tree silhouette", "serene landscapes", "beautiful nature", "vacation goals", "island getaway", "seascape photography", "calm ocean", "summer vibes", "dream destination"],
# #     "alt_text": "A breathtaking wide-angle shot of a vibrant orange and pink sunset reflecting over a calm ocean. On the right side, the dark silhouettes of several tall palm trees stand against the colorful sky, creating a peaceful and tropical scene."
# #   }
# # }
# # </EXAMPLE_OF_SUCCESS>
# # """

# # # --- Helper Functions for Retry Logic & Formatting ---

# # def format_feedback_for_prompt(feedback: str) -> str:
# #     """Formats validator feedback into a clear, numbered list for the LLM."""
# #     if "Failed" not in feedback:
# #         return ""
# #     issues = feedback.replace("Validation Failed. You MUST fix these issues:", "").strip().split("\n- ")
# #     valid_issues = [issue.strip() for issue in issues if issue.strip()]
# #     if not valid_issues:
# #         return ""
# #     formatted_list = "\n".join([f"{i+1}. {issue}" for i, issue in enumerate(valid_issues)])
# #     return f"""<PREVIOUS_ATTEMPT_FEEDBACK>
# # You MUST fix the following errors from your last attempt:
# # {formatted_list}
# # </PREVIOUS_ATTEMPT_FEEDBACK>"""

# # def fix_common_errors(content: Dict[str, Any]) -> Dict[str, Any]:
# #     """Applies simple, programmatic fixes to common LLM output errors before validation."""
# #     if content and 'instagram' in content and 'hashtags' in content['instagram']:
# #         hashtags = content['instagram'].get('hashtags', [])
# #         if isinstance(hashtags, list):
# #             fixed_hashtags = [h if h.startswith('#') else f"#{h}" for h in hashtags]
# #             content['instagram']['hashtags'] = fixed_hashtags
# #     return content

# # # --- LangGraph State ---
# # class GraphState(TypedDict):
# #     image_base64: str
# #     analysis: Optional[ImageAnalysis]
# #     social_content: Optional[SocialMediaContent]
# #     validation_feedback: str
# #     retry_count: int
# #     max_retries: int
# #     error_history: List[str]

# # # --- Validator ---
# # def comprehensive_content_validator(content: Dict[str, Any]) -> str:
# #     issues = []
# #     try:
# #         ig = content['instagram']
# #         if len(ig['caption']) > 2200: issues.append("Instagram Caption: Exceeds 2,200 characters.")
# #         if len(ig['alt_text']) > 100: issues.append("Instagram Alt Text: Exceeds 100 characters.")
# #         if not (15 <= len(ig['hashtags']) <= 30): issues.append(f"Instagram Hashtags: Incorrect count ({len(ig['hashtags'])}). Must be 15-30.")
# #         if missing := [h for h in ig['hashtags'] if not h.startswith('#')]: issues.append(f"Instagram Hashtags: Missing '#' on: {missing[:3]}")

# #         pin = content['pinterest']
# #         if len(pin['title']) > 100: issues.append("Pinterest Title: Exceeds 100 characters.")
# #         if len(pin['description']) > 500: issues.append("Pinterest Description: Exceeds 500 characters.")
# #         if not (15 <= len(pin['keywords']) <= 20): issues.append(f"Pinterest Keywords: Incorrect count ({len(pin['keywords'])}). Must be 15-20.")
# #         if has_hash := [k for k in pin['keywords'] if k.startswith('#')]: issues.append(f"Pinterest Keywords: Should not have '#': {has_hash[:3]}")
# #     except KeyError as e:
# #         issues.append(f"A required field is missing from the AI's response: {e}")

# #     return "\n- ".join(["Validation Failed. You MUST fix these issues:"] + issues) if issues else "Validation Passed"

# # # --- LangGraph Nodes ---
# # def analyze_image_node(state: GraphState):
# #     st.write("Step 1: 🧐 Analyzing image...")
# #     model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1)
# #     parser = JsonOutputParser(pydantic_object=ImageAnalysis)
# #     prompt = f"Analyze the image for social media. Output JSON only. Schema: {parser.get_format_instructions()}"
# #     message = HumanMessage(content=[{"type": "text", "text": prompt}, {"type": "image_url", "image_url": f"data:image/jpeg;base64,{state['image_base64']}"}])
# #     try:
# #         analysis = (model | parser).invoke([message])
# #         return {"analysis": analysis, "retry_count": 0, "error_history": []}
# #     except Exception as e:
# #         return {"error_history": [f"Image Analysis Failed: {e}"]}

# # def create_social_content_node(state: GraphState):
# #     retry_count = state.get('retry_count', 0)
# #     st.write(f"Step 2: ✍️ Crafting content (Attempt #{retry_count + 1})...")
# #     analysis = state['analysis']
# #     feedback = state.get('validation_feedback', '')
# #     formatted_feedback = format_feedback_for_prompt(feedback)

# #     prompt = f"""
# #     {few_shot_examples}

# #     You are a world-class social media content creator. Your task is to generate perfectly formatted content for Instagram and Pinterest based on the rules and image analysis provided. You MUST adhere to every rule.

# #     <CRITICAL_RULES>
# #     - Instagram:
# #       - caption: Maximum 2,200 characters.
# #       - hashtags: EXACTLY 15-30 items. Every single item MUST start with '#'.
# #       - alt_text: Maximum 100 characters.
# #     - Pinterest:
# #       - title: Maximum 100 characters.
# #       - description: Maximum 500 characters.
# #       - keywords: EXACTLY 15-20 items. Items must NOT start with '#'.
# #       - alt_text: Maximum 500 characters.
# #     </CRITICAL_RULES>

# #     <IMAGE_ANALYSIS>
# #     {json.dumps(analysis, indent=2)}
# #     </IMAGE_ANALYSIS>

# #     {formatted_feedback}

# #     INSTRUCTIONS:
# #     1.  Carefully review the <CRITICAL_RULES> and the <IMAGE_ANALYSIS>.
# #     2.  If <PREVIOUS_ATTEMPT_FEEDBACK> exists, you MUST correct every error listed.
# #     3.  Double-check your work before finishing. Count the hashtags and keywords. Verify the '#' formatting.
# #     4.  Your final output must be a single, valid JSON object and nothing else. Do not include any explanatory text before or after the JSON.
# #     """
    
# #     model_temperature = 0.4 if retry_count > 0 else 0.7
# #     model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=model_temperature)
# #     parser = JsonOutputParser()
# #     try:
# #         content = (model | parser).invoke(prompt)
# #         fixed_content = fix_common_errors(content)
# #         return {"social_content": fixed_content}
# #     except Exception as e:
# #         error_message = f"Content Generation Failed: {type(e).__name__} - {e}"
# #         return {"error_history": state.get("error_history", []) + [error_message]}

# # def validate_content_node(state: GraphState):
# #     st.write("Step 3: 🛡️ Validating content...")
# #     content = state.get('social_content')
# #     if not content:
# #         return {"validation_feedback": "Validation Failed: No content was generated."}
    
# #     feedback = comprehensive_content_validator(content)
# #     return {"validation_feedback": feedback}

# # def should_continue(state: GraphState):
# #     if state.get("error_history"): return "end"
# #     feedback = state.get("validation_feedback", "")
# #     if "Failed" in feedback:
# #         if state["retry_count"] >= state["max_retries"]:
# #             st.warning("⚠️ Max retries reached. Please review the final output carefully.")
# #             return "end"
# #         else:
# #             return "retry"
# #     else:
# #         st.success("✅ Content generated and validated successfully!")
# #         return "end"

# # def increment_retry_node(state: GraphState):
# #     return {"retry_count": state["retry_count"] + 1}

# # # --- Build the Graph ---
# # workflow = StateGraph(GraphState)
# # workflow.add_node("analyzer", analyze_image_node)
# # workflow.add_node("content_creator", create_social_content_node)
# # workflow.add_node("validator", validate_content_node)
# # workflow.add_node("retry_counter", increment_retry_node)
# # workflow.set_entry_point("analyzer")
# # workflow.add_edge("analyzer", "content_creator")
# # workflow.add_edge("content_creator", "validator")
# # workflow.add_conditional_edges("validator", should_continue, {"retry": "retry_counter", "end": END})
# # workflow.add_edge("retry_counter", "content_creator")
# # app = workflow.compile()

# # # --- Streamlit UI ---
# # st.title("🚀 Pro Social Media Content Generator")
# # st.markdown("Upload an image to get validated, ready-to-post content for Instagram & Pinterest.")

# # uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
# # results_container = st.container(border=True)

# # if uploaded_file:
# #     with results_container:
# #         st.image(uploaded_file, caption="Uploaded Image", width=350)
    
# #     if st.button("✨ Generate Content", type="primary", use_container_width=True):
# #         with results_container:
# #             with st.status("Generating content...", expanded=True) as status:
# #                 try:
# #                     img = Image.open(uploaded_file)
# #                     buffered = BytesIO()
# #                     if img.mode == 'RGBA': img = img.convert('RGB')
# #                     img.save(buffered, format="JPEG")
# #                     img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    
# #                     # Increased max_retries to 3 (4 total attempts)
# #                     inputs = {"image_base64": img_base64, "max_retries": 3, "retry_count": 0}
# #                     final_state = app.invoke(inputs)

# #                     content = final_state.get('social_content')
# #                     status.update(label="Process complete!", state="complete")
                    
# #                     if content:
# #                         st.divider()
# #                         col1, col2 = st.columns(2)
                        
# #                         with col1:
# #                             st.subheader("📱 Instagram")
# #                             ig = content.get('instagram', {})
# #                             caption_text = ig.get('caption', '')
# #                             st.text_area("Caption", value=caption_text, height=200, key="ig_cap")
# #                             if st.button("Copy Caption", key="copy_ig_cap"):
# #                                 copy_to_clipboard(caption_text)
# #                                 st.toast("Caption copied!")
                            
# #                             hashtags_text = " ".join(ig.get('hashtags', []))
# #                             st.text_area("Hashtags", value=hashtags_text, height=100, key="ig_tags")
# #                             if st.button("Copy Hashtags", key="copy_ig_tags"):
# #                                 copy_to_clipboard(hashtags_text)
# #                                 st.toast("Hashtags copied!")
                            
# #                             alt_text_ig = ig.get('alt_text', '')
# #                             st.text_area("Alt Text", value=alt_text_ig, height=80, key="ig_alt")
# #                             if st.button("Copy Alt Text", key="copy_ig_alt"):
# #                                 copy_to_clipboard(alt_text_ig)
# #                                 st.toast("Alt Text copied!")

# #                         with col2:
# #                             st.subheader("📌 Pinterest")
# #                             pin = content.get('pinterest', {})
# #                             title_text = pin.get('title', '')
# #                             st.text_area("Title", value=title_text, height=60, key="pin_title")
# #                             if st.button("Copy Title", key="copy_pin_title"):
# #                                 copy_to_clipboard(title_text)
# #                                 st.toast("Title copied!")
                            
# #                             desc_text = pin.get('description', '')
# #                             st.text_area("Description", value=desc_text, height=120, key="pin_desc")
# #                             if st.button("Copy Description", key="copy_pin_desc"):
# #                                 copy_to_clipboard(desc_text)
# #                                 st.toast("Description copied!")
                            
# #                             keywords_text = ", ".join(pin.get('keywords', []))
# #                             st.text_area("Keywords", value=keywords_text, height=100, key="pin_kw")
# #                             if st.button("Copy Keywords", key="copy_pin_kw"):
# #                                 copy_to_clipboard(keywords_text)
# #                                 st.toast("Keywords copied!")
                            
# #                             alt_text_pin = pin.get('alt_text', '')
# #                             st.text_area("Alt Text", value=alt_text_pin, height=100, key="pin_alt")
# #                             if st.button("Copy Alt Text ", key="copy_pin_alt"):
# #                                 copy_to_clipboard(alt_text_pin)
# #                                 st.toast("Alt Text copied!")
                    
# #                     if final_state.get('error_history'):
# #                         st.error("An error occurred during the process:")
# #                         st.json(final_state['error_history'])

# #                 except ResourceExhausted:
# #                     st.error("🚦 API Rate Limit Exceeded. Please wait a minute and try again.")
# #                 except Exception as e:
# #                     st.error(f"A critical application error occurred: {e}")












# # # main_app.py
# # import streamlit as st
# # import os
# # import base64
# # import json
# # from PIL import Image
# # from io import BytesIO
# # from typing import List, Dict, Any, Optional, Type

# # # --- Core Dependencies ---
# # # Make sure to install them:
# # # pip install streamlit pydantic langchain-google-genai streamlit-extras
# # from pydantic import BaseModel, Field
# # from langchain_google_genai import ChatGoogleGenerativeAI
# # from langchain_core.messages import HumanMessage
# # from langchain_core.output_parsers.json import JsonOutputParser
# # from streamlit_extras.copy_to_clipboard import copy_to_clipboard

# # # --- Page & Session State Configuration ---
# # st.set_page_config(
# #     page_title="AI Social Content Generator 📱✨",
# #     page_icon="🚀",
# #     layout="wide",
# # )

# # # Initialize session state to hold user inputs and generated content
# # if "generated_content" not in st.session_state:
# #     st.session_state.generated_content = {}
# # if "image_base64" not in st.session_state:
# #     st.session_state.image_base64 = None
# # if "platforms_selected" not in st.session_state:
# #     st.session_state.platforms_selected = []
# # if "business_context" not in st.session_state:
# #     st.session_state.business_context = ""
# # if "last_uploaded_filename" not in st.session_state:
# #     st.session_state.last_uploaded_filename = None


# # # --- Helper Function for Loading Icons ---
# # # This helps embed icons directly into the app without extra files
# # def load_image_as_base64(path):
# #     with open(path, "rb") as f:
# #         return base64.b64encode(f.read()).decode()

# # # --- Pydantic Models for Structured Output ---
# # # Defines the expected structure for each social media platform's content

# # class InstagramContent(BaseModel):
# #     caption: str = Field(description="Engaging Instagram caption (max 2,200 chars), use emojis.")
# #     hashtags: List[str] = Field(description="List of 15-20 relevant hashtags, each starting with '#'.")
# #     alt_text: str = Field(description="Descriptive alt text for accessibility (max 125 chars).")

# # class FacebookContent(BaseModel):
# #     post_text: str = Field(description="Compelling Facebook post text, can be longer and more detailed. Use emojis and ask a question to encourage engagement.")
# #     headline: Optional[str] = Field(description="An optional catchy headline if the post is promotional.")
# #     link_description: Optional[str] = Field(description="A brief description for a shared link.")

# # class XContent(BaseModel):
# #     tweet: str = Field(description="Concise and impactful tweet (max 280 chars). Use emojis and 2-3 key hashtags.")
# #     hashtags: List[str] = Field(description="A list of 2-3 relevant hashtags for the tweet, each starting with '#'.")

# # class PinterestContent(BaseModel):
# #     title: str = Field(description="SEO-friendly Pinterest pin title (max 100 chars).")
# #     description: str = Field(description="Detailed description with keywords (max 500 chars).")
# #     keywords: List[str] = Field(description="List of 10-15 keywords, without '#'.")

# # class LinkedInContent(BaseModel):
# #     post_text: str = Field(description="Professional and insightful LinkedIn post. Share expertise or company news. Use 3-5 professional hashtags.")
# #     hashtags: List[str] = Field(description="List of 3-5 professional hashtags, each starting with '#'.")

# # # --- Platform Configuration: The "Single Source of Truth" ---
# # # This dictionary makes the app modular. To add a new platform, just add an entry here.
# # PLATFORM_CONFIG = {
# #     "instagram": {
# #         "name": "Instagram",
# #         "icon": "icons/instagram.png", # Make sure you have these icon files
# #         "pydantic_model": InstagramContent,
# #         "prompt": "Generate an engaging caption, 15-20 relevant hashtags, and descriptive alt text for an Instagram post."
# #     },
# #     "facebook": {
# #         "name": "Facebook",
# #         "icon": "icons/facebook.png",
# #         "pydantic_model": FacebookContent,
# #         "prompt": "Create a compelling Facebook post with an optional headline. The tone can be more detailed and community-focused. Ask a question to drive comments."
# #     },
# #     "x": {
# #         "name": "X (Twitter)",
# #         "icon": "icons/x.png",
# #         "pydantic_model": XContent,
# #         "prompt": "Write a short, punchy tweet (under 280 characters) with 2-3 key hashtags."
# #     },
# #     "pinterest": {
# #         "name": "Pinterest",
# #         "icon": "icons/pinterest.png",
# #         "pydantic_model": PinterestContent,
# #         "prompt": "Create a keyword-rich title and description for a Pinterest pin. Also provide a list of 10-15 relevant keywords."
# #     },
# #     "linkedin": {
# #         "name": "LinkedIn",
# #         "icon": "icons/linkedin.png",
# #         "pydantic_model": LinkedInContent,
# #         "prompt": "Compose a professional LinkedIn post. The tone should be informative, industry-relevant, or share company insights. Include 3-5 professional hashtags."
# #     }
# # }


# # # --- Core Generation Function ---
# # def generate_for_platform(platform_key: str, image_base64: str, business_context: str, pydantic_model: Type[BaseModel]):
# #     """Generates content for a single platform using the Gemini model."""
# #     config = PLATFORM_CONFIG[platform_key]
# #     parser = JsonOutputParser(pydantic_object=pydantic_model)
    
# #     # Construct a detailed prompt for the AI
# #     prompt_text = f"""
# #     You are an expert social media manager. Your task is to create content for {config['name']} based on the provided image and business context.

# #     **Business Context:**
# #     {business_context if business_context else "Not provided. Analyze the image for general appeal."}

# #     **Platform Instructions ({config['name']}):**
# #     {config['prompt']}

# #     **Output Format:**
# #     You MUST provide your response in a valid JSON object that strictly follows this schema. Do not add any text before or after the JSON.
# #     Schema:
# #     {parser.get_format_instructions()}
# #     """
    
# #     try:
# #         model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)
# #         message = HumanMessage(
# #             content=[
# #                 {"type": "text", "text": prompt_text},
# #                 {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_base64}"}
# #             ]
# #         )
        
# #         response = model.invoke([message])
# #         parsed_content = parser.parse(response.content)
# #         return parsed_content
        
# #     except Exception as e:
# #         st.error(f"Error generating content for {config['name']}: {e}")
# #         return None

# # # --- UI Layout ---

# # st.title("🚀 AI Social Media Content Generator")
# # st.markdown("Upload an image, describe your business (optional), select your social platforms, and let AI do the rest!")

# # # --- Main Columns for Input ---
# # col1, col2 = st.columns([2, 3])

# # with col1:
# #     st.subheader("1. Upload Your Image")
# #     uploaded_file = st.file_uploader(
# #         "Click to upload...",
# #         type=["jpg", "jpeg", "png"],
# #         label_visibility="collapsed"
# #     )

# #     # --- Image Processing and State Management ---
# #     if uploaded_file:
# #         # Reset if a new image is uploaded
# #         if st.session_state.last_uploaded_filename != uploaded_file.name:
# #             st.session_state.generated_content = {}
# #             st.session_state.last_uploaded_filename = uploaded_file.name
        
# #         img = Image.open(uploaded_file)
# #         # Display a smaller preview
# #         st.image(img, caption="Your image", width=300)
        
# #         buffered = BytesIO()
# #         if img.mode == 'RGBA':
# #             img = img.convert('RGB')
# #         img.save(buffered, format="JPEG")
# #         st.session_state.image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
# #     st.session_state.business_context = st.text_area(
# #         "2. Describe Your Work (Optional)",
# #         value=st.session_state.business_context,
# #         placeholder="e.g., I sell handmade scented candles online.",
# #         help="Providing context helps the AI generate more relevant posts!"
# #     )

# # with col2:
# #     st.subheader("3. Select Platforms")
    
# #     # Dynamically create checkboxes for each platform from the config
# #     selected_platforms = []
# #     num_columns = 5
# #     icon_cols = st.columns(num_columns)
    
# #     for i, (key, config) in enumerate(PLATFORM_CONFIG.items()):
# #         with icon_cols[i % num_columns]:
# #             # Use HTML for custom styling of the icon and checkbox
# #             st.markdown(f"<p style='text-align: center;'>{config['name']}</p>", unsafe_allow_html=True)
# #             st.image(config['icon'], width=60)
# #             if st.checkbox("", key=f"cb_{key}", value=(key in st.session_state.platforms_selected)):
# #                 selected_platforms.append(key)

# #     st.session_state.platforms_selected = selected_platforms
    
# #     st.markdown("---") # Visual separator
    
# #     # --- Action Buttons ---
# #     can_generate = st.session_state.image_base64 and st.session_state.platforms_selected
    
# #     if st.button("✨ Generate Content", type="primary", use_container_width=True, disabled=not can_generate):
# #         with st.status("Generating content...", expanded=True) as status:
# #             st.session_state.generated_content = {} # Clear previous results
# #             for platform_key in st.session_state.platforms_selected:
# #                 platform_name = PLATFORM_CONFIG[platform_key]['name']
# #                 status.update(label=f"✍️ Crafting post for {platform_name}...")
# #                 content = generate_for_platform(
# #                     platform_key,
# #                     st.session_state.image_base64,
# #                     st.session_state.business_context,
# #                     PLATFORM_CONFIG[platform_key]['pydantic_model']
# #                 )
# #                 if content:
# #                     st.session_state.generated_content[platform_key] = content
# #             status.update(label="✅ All content generated!", state="complete")

# # # --- Display Generated Content ---
# # if st.session_state.generated_content:
# #     st.markdown("---")
# #     st.subheader("🎉 Your Generated Content")

# #     # Create tabs for each platform that has content
# #     platform_keys_with_content = [
# #         key for key in st.session_state.platforms_selected 
# #         if key in st.session_state.generated_content
# #     ]
    
# #     tabs = st.tabs([PLATFORM_CONFIG[key]['name'] for key in platform_keys_with_content])

# #     for i, tab in enumerate(tabs):
# #         platform_key = platform_keys_with_content[i]
# #         content_data = st.session_state.generated_content[platform_key]
        
# #         with tab:
# #             # Iterate through the fields of the Pydantic model
# #             for field, value in content_data.items():
# #                 field_title = field.replace('_', ' ').title()
                
# #                 # Format lists nicely
# #                 if isinstance(value, list):
# #                     display_value = " ".join(value) if field == 'hashtags' else ", ".join(value)
# #                 else:
# #                     display_value = value if value else "N/A"

# #                 st.text_area(field_title, value=display_value, height=150 if len(display_value) > 100 else 75, key=f"{platform_key}_{field}")
                
# #                 if st.button(f"Copy {field_title}", key=f"copy_{platform_key}_{field}"):
# #                     copy_to_clipboard(display_value)
# #                     st.toast(f"{field_title} copied to clipboard!")

# #     # "Try Another" button appears with the results
# #     if st.button("🔄 Try Another Version", use_container_width=True):
# #         # This will trigger a re-run of the generation logic above
# #         with st.spinner("Regenerating new versions..."):
# #             st.session_state.generated_content = {} # Clear old results before regenerating
# #             for platform_key in st.session_state.platforms_selected:
# #                  content = generate_for_platform(
# #                     platform_key,
# #                     st.session_state.image_base64,
# #                     st.session_state.business_context,
# #                     PLATFORM_CONFIG[platform_key]['pydantic_model']
# #                 )
# #                  if content:
# #                     st.session_state.generated_content[platform_key] = content
# #         st.rerun() # Rerun the script to display the new content
