import pymysql
import os

def extract_all_keys():
    try:
        connection = pymysql.connect(
            host="127.0.0.1", port=3307, user="root", password="", database="apsdreamhome"
        )
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES;")
            tables = [t[0] for t in cursor.fetchall()]
            
            found_keys = {}
            for table in tables:
                cursor.execute(f"SELECT * FROM `{table}`")
                for row in cursor.fetchall():
                    for val in row:
                        if isinstance(val, str):
                            if val.startswith("AIza"):
                                found_keys["GEMINI_API_KEY"] = val
                            elif val.startswith("sk-or-"):
                                found_keys["OPENROUTER_API_KEY"] = val
                            elif val.startswith("sk-proj-"):
                                found_keys["OPENAI_API_KEY"] = val
                            elif val.startswith("sk-ant-"):
                                found_keys["ANTHROPIC_API_KEY"] = val
                            elif val.startswith("hf_"):
                                found_keys["HUGGING_FACE_API_KEY"] = val

            print("Found Keys:")
            for k, v in found_keys.items():
                print(f"{k}: {v[:15]}...{v[-5:]} (Length: {len(v)})")
                
            if found_keys:
                env_lines = []
                if os.path.exists(".env"):
                    with open(".env", "r", encoding="utf-8") as f:
                        env_lines = f.readlines()
                
                for k, v in found_keys.items():
                    replaced = False
                    for i, line in enumerate(env_lines):
                        if line.startswith(f"{k}="):
                            env_lines[i] = f"{k}={v}\n"
                            replaced = True
                            break
                    if not replaced:
                        env_lines.append(f"{k}={v}\n")
                        
                with open(".env", "w", encoding="utf-8") as f:
                    f.writelines(env_lines)
                print("\nAll keys successfully saved to .env file!")
            else:
                print("No keys found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_all_keys()
