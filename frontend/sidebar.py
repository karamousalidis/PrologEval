import streamlit as st


def display_sidebar() -> None:
    """Renders the session history in the sidebar."""
    st.sidebar.title("Session History")

    if not st.session_state.history:
        st.sidebar.info("No generations yet.")
    else:
        for i, record in enumerate(reversed(st.session_state.history)):
            models_str = ", ".join(record.get('models', [record.get('model', 'Unknown')]))
            with st.sidebar.expander(f"Run {len(st.session_state.history) - i}: {models_str}"):
                st.write(f"**Prompt:** {record.get('user_prompt', '')[:50]}...")
                
                # Support legacy single-model format and new dual-model format
                results = record.get('results', {record.get('model', 'Unknown'): record})
                
                for model_name, res in results.items():
                    if len(results) > 1:
                        st.markdown(f"**{model_name}**")
                        
                    if "error" in res:
                        st.error(res["error"])
                        continue
                        
                    st.write(f"Time Taken: {res.get('time_taken', 0):.2f}s")
                    st.write(f"Tokens: {res.get('tokens_prompt', '?')}/{res.get('tokens_completion', '?')}")
                    
                    r_score = res.get('readability_score', 'N/A')
                    if isinstance(r_score, (float, int)):
                        r_score = f"{r_score:.2f}"
                    st.write(f"Readability Score: {r_score}")
                    
                    gen_text = res.get('generated_text', res.get('text', ''))
                    st.download_button(
                        label=f"Download {model_name} Code",
                        data=gen_text,
                        file_name=f"generated_code_{model_name.replace(' ', '_')}_{len(st.session_state.history) - i}.pl",
                        mime="text/plain",
                        key=f"dl_btn_{i}_{model_name}",
                        use_container_width=True
                    )
        
        st.sidebar.divider()
        if st.sidebar.button("Clear History", use_container_width=True):
            st.session_state.history = []
            st.rerun()
