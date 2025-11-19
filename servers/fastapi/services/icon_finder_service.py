import asyncio
import json

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
        """Initialize the ChromaDB collection for icon search."""
        try:
            self.embedding_function = ONNXMiniLM_L6_V2()
            self.embedding_function.DOWNLOAD_PATH = "chroma/models"
            self.embedding_function._download_model_if_not_exists()
            
            # Try to get existing collection first
            try:
                self.collection = self.client.get_collection(
                    self.collection_name, embedding_function=self.embedding_function
                )
                return
            except Exception:
                # Collection doesn't exist, create it
                pass
            
            # Load icons from file
            icons_path = "assets/icons.json"
            try:
                with open(icons_path, "r") as f:
                    icons = json.load(f)
            except FileNotFoundError:
                print(f"Icons file not found at {icons_path}")
                self.chromadb_enabled = False
                return
            except json.JSONDecodeError as e:
                print(f"Error parsing icons JSON: {e}")
                self.chromadb_enabled = False
                return

            documents = []
            ids = []

            # Process icons and build documents for embedding
            if "icons" in icons:
                for i, each in enumerate(icons["icons"]):
                    if each.get("name", "").split("-")[-1] == "bold":
                        doc_text = f"{each.get('name', '')} {each.get('tags', '')}"
                        documents.append(doc_text)
                        ids.append(each["name"])

            # Create collection if we have documents
            if documents:
                try:
                    self.collection = self.client.create_collection(
                        name=self.collection_name,
                        embedding_function=self.embedding_function,
                        metadata={"hnsw:space": "cosine"},
                    )
                    self.collection.add(documents=documents, ids=ids)
                except Exception as e:
                    print(f"Failed to create or populate collection: {e}")
                    self.chromadb_enabled = False
            else:
                print("No valid icons found to populate collection")
                self.chromadb_enabled = False
                
        except Exception as e:
            print(f"Error initializing icons collection: {e}")
            self.chromadb_enabled = False

    async def search_icons(self, query: str, k: int = 1):
        """Search for icons based on query. Falls back to default icon if ChromaDB unavailable."""
        if not self.chromadb_enabled or not hasattr(self, 'collection'):
            # Fallback to default icon when ChromaDB is not available
            return ["/static/icons/bold/document.svg"]
        
        try:
            result = await asyncio.to_thread(
                self.collection.query,
                query_texts=[query],
                n_results=k,
            )
            if result and result.get("ids") and result["ids"][0]:
                return [f"/static/icons/bold/{icon}.svg" for icon in result["ids"][0]]
            else:
                # Return default icon if no results found
                return ["/static/icons/bold/document.svg"]
        except Exception as e:
            print(f"Error searching icons: {e}")
            return ["/static/icons/bold/document.svg"]


ICON_FINDER_SERVICE = IconFinderService()
