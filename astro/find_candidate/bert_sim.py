import os
import torch
import numpy as np
from huggingface_hub import snapshot_download
from transformers import AutoModel, AutoTokenizer
from sklearn.metrics.pairwise import cosine_similarity

class SimilarityModel:
    def __init__(self, model_dir="models/minilm"):
        """
               MiniLM   （     ）。
        
          :
        - model_dir (str):            ，   "models/minilm"。
        """
        self.model_dir = model_dir
        self.tokenizer, self.model = self._load_model()

    def _load_model(self):
        """
              `all-MiniLM-L6-v2`   。       ，     。
        
          :
        - tokenizer:      
        - model:       
        """
        if not os.path.exists(self.model_dir):
            print(f"🔽       {self.model_dir}...")
            snapshot_download(repo_id="sentence-transformers/all-MiniLM-L6-v2", local_dir=self.model_dir)

        tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
        model = AutoModel.from_pretrained(self.model_dir)
        print("✅       ！")
        return tokenizer, model

    def _compute_sentence_embedding(self, sentence):
        """
                   。
        
          :
        - sentence (str):        
        
          :
        -     384       (numpy array)
        """
        inputs = self.tokenizer(sentence, return_tensors="pt", truncation=True, padding=True)
        
        #          
        with torch.no_grad():
            outputs = self.model(**inputs)

        #        hidden state        
        sentence_embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
        
        return sentence_embedding

    def compute_similarity(self, sentence1, sentence2):
        """
                  （       ）。
        
          :
        - sentence1 (str):    1
        - sentence2 (str):    2
        
          :
        -       (float):      [0, 1]，1       
        """
        embedding1 = self._compute_sentence_embedding(sentence1)
        embedding2 = self._compute_sentence_embedding(sentence2)

        #        
        similarity_score = cosine_similarity([embedding1], [embedding2])[0][0]

        return similarity_score
