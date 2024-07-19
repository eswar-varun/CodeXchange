import streamlit as st
import google.generativeai as palm

# Path to your service account key file
palm.configure(api_key="your-api-key")



chat_model = "models/chat-bison-001"


def translate_code(source_code, source_lang, target_lang):
    context = f"You are a highly skilled software developer with expertise in multiple programming languages. Translate the following {source_lang} code to {target_lang}. Ensure that the functionality remains the same and that you follow best practices and idioms of the {target_lang} language.I want you to give only the code no need any other explainations.\n\n {source_code}"
    response = palm.chat(model=chat_model,messages=[context])
    return str(response.candidates[0]["content"][3:len(response.candidates[0]["content"])-4])

st.set_page_config(layout="wide")  # Set the layout to wide



st.title("CodeXchange: Revolutionizing Code Translation and Collaboration")

st.markdown("""
**CodeXchange** is an innovative web application designed to streamline code translation and facilitate seamless collaboration among developers working with different programming languages. Whether you're transitioning applications between platforms, collaborating in multilingual teams, or reusing code across projects, CodeXchange empowers developers to effortlessly translate code snippets between various programming languages. Leveraging advanced translation algorithms and syntax analysis, CodeXchange ensures accurate and reliable code conversion while preserving the original functionality and logic. With its intuitive interface and comprehensive language support, CodeXchange revolutionizes the development workflow, enabling teams to work together efficiently, enhance code reusability, and accelerate project delivery.
""")

st.markdown("## Scenario 1: Platform Transition")

st.markdown("""
CodeXchange assists developers in transitioning applications from one platform to another. For instance, a team working on an application written in Python needs to migrate it to Java to leverage Java's robustness and scalability in an enterprise environment. By inputting the Python code snippets and selecting Java as the target language, developers receive accurately translated code that maintains the original functionality, streamlining the migration process and minimizing the risk of introducing errors.
""")

st.markdown("## Scenario 2: Multilingual Collaboration")

st.markdown("""
In a collaborative project where team members use different programming languages, CodeXchange facilitates seamless integration by translating code snippets as needed. Suppose one part of the team is proficient in C++ while another prefers Python. Developers can write code in their preferred language and use CodeXchange to translate it, ensuring all team members can work together efficiently without being constrained by language barriers. This enhances productivity and reduces the learning curve associated with adopting new languages.
""")

st.markdown("## Scenario 3: Code Reusability Across Projects")

st.markdown("""
CodeXchange promotes code reusability by enabling developers to translate existing code into different languages for new projects. For example, a developer has written a set of utility functions in Java that would be beneficial for a new project being developed in C++. By translating these Java functions into C++ using CodeXchange, the developer can quickly integrate proven code into the new project, saving time and ensuring consistency across different projects.
""")


col1, col2 = st.columns([0.5,0.5], gap="large")

with col1:
    source_lang = st.selectbox("Select Source Language", ["Java", "Python", "JavaScript", "C++", "Ruby", "PHP", "Go", "Swift", "Kotlin", "TypeScript"])
    source_code = st.text_area("Source Code", height=600)  # Increase the height
    a=st.button("Translate")

with col2:
    target_lang = st.selectbox("Select Target Language", ["Python", "Java", "JavaScript", "C++", "Ruby", "PHP", "Go", "Swift", "Kotlin", "TypeScript"])
    if a:
        if source_code:
            translated_code = translate_code(source_code, source_lang, target_lang)
        else:
            st.warning("Please enter the source code to translate.")
    if 'translated_code' in locals():
        st.success("CODE TRANSALATION DONE")
        st.code(translated_code,language=target_lang.lower(),line_numbers=True)


st.markdown("""
<style>
    .main {
        padding: 1rem;
        font-size:42px;
    }
    .block-container {
        padding: 2rem 1rem 10rem;
        background-color: #ffffff;
        border-radius: 10px;
        box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);
    }
    .stButton > button {
        background-color: green;
        color: white;
        border: white;
        border-radius: 5px;
        padding: 1rem 2rem;
        font-size: 5px;
        cursor: pointer;
    }
    .stTextInput > div > input, .stTextArea > div > textarea, .stSelectbox > div > select {
        border-radius: 5px;
        border: 1px solid #ccc;
        padding: 1rem;
        font-size: 10px;
    }
</style>
""", unsafe_allow_html=True)
