import asyncio
import json
import os
import sys

# Try to patch SQLite before importing chromadb
try:
    from sqlite_patcher import patch_sqlite
    patch_sqlite()
except ImportError:
    pass

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
    CHROMADB_AVAILABLE = True
    print("ChromaDB is available")
except (ImportError, RuntimeError) as e:
    print(f"ChromaDB not available: {e}")
    CHROMADB_AVAILABLE = False


class IconFinderService:
    def __init__(self):
        self.collection_name = "icons"
        
        if CHROMADB_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(
                    path="chroma", settings=Settings(anonymized_telemetry=False)
                )
                print("Initializing icons collection...")
                self._initialize_icons_collection()
                print("Icons collection initialized.")
                self.chromadb_enabled = True
            except Exception as e:
                print(f"Failed to initialize ChromaDB: {e}")
                print("Falling back to static icon matching...")
                self.chromadb_enabled = False
        else:
            print("ChromaDB not available, using static icon matching...")
            self.chromadb_enabled = False

    def _initialize_icons_collection(self):
        if not CHROMADB_AVAILABLE:
            return
            
        self.embedding_function = ONNXMiniLM_L6_V2()
        self.embedding_function.DOWNLOAD_PATH = "chroma/models"
        self.embedding_function._download_model_if_not_exists()
        try:
            self.collection = self.client.get_collection(
                self.collection_name, embedding_function=self.embedding_function
            )
        except Exception:
            with open("assets/icons.json", "r") as f:
                icons = json.load(f)

            documents = []
            ids = []

            for i, each in enumerate(icons["icons"]):
                if each["name"].split("-")[-1] == "bold":
                    doc_text = f"{each['name']} {each['tags']}"
                    documents.append(doc_text)
                    ids.append(each["name"])

            if documents:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"},
                )
                self.collection.add(documents=documents, ids=ids)

    def _fallback_search_icons(self, query: str, k: int = 1):
        """Fallback method when ChromaDB is not available"""
        try:
            with open("assets/icons.json", "r") as f:
                icons = json.load(f)
            
            # Simple keyword matching
            query_lower = query.lower()
            matches = []
            
            for icon in icons["icons"]:
                if icon["name"].split("-")[-1] == "bold":
                    name_match = query_lower in icon["name"].lower()
                    tags_match = any(query_lower in tag.lower() for tag in icon.get("tags", []))
                    
                    if name_match or tags_match:
                        matches.append(icon["name"])
            
            # Return top k matches or default icons if no matches
            if matches:
                return matches[:k]
            else:
                # Return some default icons
                default_icons = ["document-text-bold", "presentation-bold", "file-bold"]
                return default_icons[:k]
        except Exception as e:
            print(f"Error in fallback icon search: {e}")
            return ["document-text-bold"]

    async def search_icons(self, query: str, k: int = 1):
        if not self.chromadb_enabled:
            # Use fallback method
            icon_names = self._fallback_search_icons(query, k)
            return [f"/static/icons/bold/{name}.svg" for name in icon_names]
        
        try:
            result = await asyncio.to_thread(
                self.collection.query,
                query_texts=[query],
                n_results=k,
            )
            return [f"/static/icons/bold/{each}.svg" for each in result["ids"][0]]
        except Exception as e:
            print(f"Error in ChromaDB icon search: {e}")
            # Fall back to static search
            icon_names = self._fallback_search_icons(query, k)
            return [f"/static/icons/bold/{name}.svg" for name in icon_names]


ICON_FINDER_SERVICE = IconFinderService()
