# pest_detection.py
import torch
import torchvision.transforms as transforms
from PIL import Image
import os
from torchvision import models
import torch.nn as nn

class PestDetector:
    def __init__(self, model_path='best_model.pth'):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.class_names = [
            "Beet Armyworm", "Black Hairy", "Cutworm", "Field Cricket",
            "Jute Aphid", "Jute Hairy", "Jute Red Mite", "Jute Semilooper",
            "Jute Stem Girdler", "Jute Stem Weevil", "Leaf Beetle", "Mealybug",
            "Pod Borer", "Scopula Emissaria", "Termite", 
            "Termite odontotermes (Rambur)", "Yellow Mite"
        ]
        
        self.model = models.resnet50(weights='IMAGENET1K_V2')
        num_classes = len(self.class_names)
        self.model.fc = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(self.model.fc.in_features, num_classes)
        )
        
        # Load the saved state dict
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model = self.model.to(self.device)
        self.model.eval()
        
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def predict(self, image_path):
        image = Image.open(image_path).convert('RGB')
        image_tensor = self.transform(image).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(image_tensor)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
            
        return {
            'pest_type': self.class_names[predicted.item()],
            'confidence': confidence.item() * 100
        }

# The rest of the code (PestPrediction model and routes) remains the same