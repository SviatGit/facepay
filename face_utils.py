import numpy as np
from deepface import DeepFace
from scipy.spatial.distance import euclidean

def get_face_embedding(image):
    """
    Given an image (BGR from OpenCV), return the face embedding.
    """
    # DeepFace expects RGB
    img_rgb = image[:, :, ::-1]
    embedding_obj = DeepFace.represent(img_path=img_rgb, model_name="Facenet")[0]
    return embedding_obj["embedding"]

def match_face(captured_embedding, users, threshold=10):
    """
    Compare the captured face embedding with stored users.
    Returns matched user dict or None.
    """
    for user in users:
        stored_embedding = user.get("face_embedding")
        if not stored_embedding:
            continue

        dist = euclidean(captured_embedding, stored_embedding)
        if dist < threshold:
            return user  # Match found
    return None