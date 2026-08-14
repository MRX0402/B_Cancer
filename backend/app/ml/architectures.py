"""
app/ml/architectures.py
========================
Foydalanuvchi tomonidan ta'minlangan `models/architectures.py` bilan BIR XIL
arxitektura (EfficientNet-B3 + ResNet-50 + DenseNet-121 ensemble), faqat
import yo'li (`.config`) va checkpoint yuklash logikasi inference uchun
moslashtirilgan. Hugging Face'dagi `ensemble_best.pth` shu klasslarning
`state_dict()`iga to'g'ri keladi.

Bu modul faqat torch/torchvision o'rnatilgan bo'lsa import qilinadi — chaqiruvchi
(`inference.py`) buni try/except bilan lazy import qiladi, shuning uchun bu yerda
importlarni to'g'ridan-to'g'ri qilish xavfsiz.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models

from .config import NUM_CLASSES, ENSEMBLE_WEIGHTS


def _adapt_first_conv(model, layer_path: list, pretrained_weight: torch.Tensor):
    """RGB (3-kanal) pretrained og'irliklarni grayscale (1-kanal)ga moslashtiradi."""
    adapted = pretrained_weight.mean(dim=1, keepdim=True)

    obj = model
    for attr in layer_path[:-1]:
        obj = getattr(obj, attr)
    layer = getattr(obj, layer_path[-1])

    new_conv = nn.Conv2d(
        1, layer.out_channels,
        kernel_size=layer.kernel_size,
        stride=layer.stride,
        padding=layer.padding,
        bias=(layer.bias is not None)
    )
    new_conv.weight = nn.Parameter(adapted)
    if layer.bias is not None:
        new_conv.bias = nn.Parameter(layer.bias.clone())

    setattr(obj, layer_path[-1], new_conv)


class EfficientNetB3(nn.Module):
    def __init__(self, num_classes: int = NUM_CLASSES, dropout: float = 0.4, pretrained: bool = False):
        super().__init__()
        weights = models.EfficientNet_B3_Weights.IMAGENET1K_V1 if pretrained else None
        backbone = models.efficientnet_b3(weights=weights)
        first_w = backbone.features[0][0].weight.data.clone()
        _adapt_first_conv(backbone, ['features', '0', '0'], first_w)

        self.backbone = backbone.features
        self.pool = nn.AdaptiveAvgPool2d(1)

        in_features = 1536
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(in_features, 512),
            nn.SiLU(),
            nn.Dropout(dropout / 2),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        x = self.backbone(x)
        x = self.pool(x).flatten(1)
        return self.classifier(x)

    def get_probabilities(self, x):
        return F.softmax(self.forward(x), dim=1)


class ResNet50(nn.Module):
    def __init__(self, num_classes: int = NUM_CLASSES, dropout: float = 0.4, pretrained: bool = False):
        super().__init__()
        weights = models.ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
        backbone = models.resnet50(weights=weights)

        first_w = backbone.conv1.weight.data.clone()
        _adapt_first_conv(backbone, ['conv1'], first_w)

        in_features = backbone.fc.in_features
        backbone.fc = nn.Identity()

        self.backbone = backbone
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.Dropout(dropout / 2),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        x = self.backbone(x)
        return self.classifier(x)

    def get_probabilities(self, x):
        return F.softmax(self.forward(x), dim=1)


class DenseNet121(nn.Module):
    def __init__(self, num_classes: int = NUM_CLASSES, dropout: float = 0.4, pretrained: bool = False):
        super().__init__()
        weights = models.DenseNet121_Weights.IMAGENET1K_V1 if pretrained else None
        backbone = models.densenet121(weights=weights)

        first_w = backbone.features.conv0.weight.data.clone()
        _adapt_first_conv(backbone, ['features', 'conv0'], first_w)

        in_features = backbone.classifier.in_features
        backbone.classifier = nn.Identity()

        self.backbone = backbone
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.Dropout(dropout / 2),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        features = self.backbone.features(x)
        x = F.relu(features, inplace=True)
        x = self.pool(x).flatten(1)
        return self.classifier(x)

    def get_probabilities(self, x):
        return F.softmax(self.forward(x), dim=1)


class EnsembleModel(nn.Module):
    """
    P_ensemble = w1*P_eff + w2*P_res + w3*P_den  (soft voting).
    Attribute nomlari (`efficientnet`, `resnet`, `densenet`) checkpoint'dagi
    state_dict kalitlariga aynan mos kelishi SHART.
    """

    def __init__(self, weights: dict = None, device=None):
        super().__init__()
        weights = weights or ENSEMBLE_WEIGHTS
        self.device = device or torch.device('cpu')

        # Inference uchun ImageNet pretrained og'irliklarni qayta yuklashning
        # hojati yo'q — checkpoint ustidan to'liq yoziladi, shuning uchun
        # pretrained=False (tezroq va internetga muhtoj emas).
        self.efficientnet = EfficientNetB3(pretrained=False)
        self.resnet = ResNet50(pretrained=False)
        self.densenet = DenseNet121(pretrained=False)

        self.w_eff = weights['efficientnet_b3']
        self.w_res = weights['resnet50']
        self.w_den = weights['densenet121']

    def forward(self, x):
        p_eff = self.efficientnet.get_probabilities(x)
        p_res = self.resnet.get_probabilities(x)
        p_den = self.densenet.get_probabilities(x)

        p_ensemble = self.w_eff * p_eff + self.w_res * p_res + self.w_den * p_den
        return torch.log(p_ensemble + 1e-8)

    def get_probabilities(self, x):
        return torch.exp(self.forward(x))
