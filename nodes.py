import keyframed as kf
from keyframed.dsl import curve_from_cn_string
import logging
import torch
#import warnings


logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


CATEGORY = "keyframed"


class KfCurveFromString:
    CATEGORY=CATEGORY
    FUNCTION = 'main'
    RETURN_TYPES = ("KEYFRAMED_CURVE",)
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {"chigozie_string": ("STRING", {
                    "multiline": True, #True if you want the field to look like the one on the ClipTextEncode node
                    "default": "0:(1)"
                }),
            },
        }
    
    def main(self, chigozie_string):
        curve = curve_from_cn_string(chigozie_string)
        return (curve,)


class KfCurveFromYAML:
    CATEGORY=CATEGORY
    FUNCTION = 'main'
    RETURN_TYPES = ("KEYFRAMED_CURVE",)
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {"yaml": ("STRING", {
                    "multiline": True, #True if you want the field to look like the one on the ClipTextEncode node
                    # TO DO: replace this with kf.serializaiton.to_dict() # or whatever
                    "default": """curve:
- - 0
  - 0
  - linear
- - 1
  - 1
loop: false
bounce: false
duration: 1
label: foo"""
                }),
            },
        }
    
    def main(self, yaml):
        curve = kf.serialization.from_yaml(yaml)
        return (curve,)


class KfEvaluateCurveAtT:
    CATEGORY=CATEGORY
    FUNCTION = 'main'
    RETURN_TYPES = ("FLOAT","INT")

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "curve": ("KEYFRAMED_CURVE",{"forceInput": True,}),
                "t": ("INT",{"default":0})
            },
        }

    def main(self, curve, t):
        return curve[t], int(curve[t])


# class KfCurveToAcnLatentKeyframe:
#     CATEGORY=CATEGORY
#     FUNCTION = 'main'
#     RETURN_NAMES = ("LATENT_KF", )
#     RETURN_TYPES = ("LATENT_KEYFRAME",)
#     """Compatibility with Kosinkadink "Advanced Controlnet" AnimateDiff"""
#     @classmethod
#     def INPUT_TYPES(s):
#         return {
#             "required": {
#                 "curve": ("KEYFRAMED_CURVE",{"forceInput": True,}),
#             },
#         }
#     def main(self, curve):
#         warnings.warn("KfCurveToAcnLatentKeyframe not implemented")
#         return (curve,)


class KfApplyCurveToCond:
    CATEGORY=CATEGORY
    FUNCTION = 'main'
    #RETURN_TYPES = ("CONDITIONING","LATENT_KEYFRAME",)
    RETURN_TYPES = ("CONDITIONING",)
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "curve": ("KEYFRAMED_CURVE", {"forceInput": True,}),
                "cond": ("CONDITIONING", {"forceInput": True,}),
            },
            "optional":{
                "latents": ("LATENT", {}),
                "start_t": ("INT", {"default":0, }),
                "n": ("INT", {}),
            },
        }
    def main(self, curve, cond, latents=None, start_t=0, n=0):
        #logger.info(f"latents: {latents}")
        logger.info(f"type(latents): {type(latents)}") # Latent is a dict that (presently) has one key, `samples`
        device = 'cpu' # probably should be handling this some other way
        #if latents is not None:
        if isinstance(latents, dict):
            if 'samples' in latents:
                n = latents['samples'].shape[0] # batch dimension
                device = latents['samples'].device
        weights = [curve[start_t+i] for i in range(n)]
        weights = torch.tensor(weights, device=device)
        cond_out = []
        for c_tensor, c_dict in cond:
            weights.to(c_tensor.device)
            m=c_tensor.shape[0]
            if c_tensor.shape[0] == 1:
                c_tensor = c_tensor.repeat(n, 1, 1) # batch, n_tokens, embeding_dim
                m=n
            #logger.info(f"c_tensor.shape:{c_tensor.shape}")
            #logger.info(f"weights.shape:{weights.shape}")
            #logger.info(f"weights.shape:{weights.view(n,1,1).shape}")
            #c_tensor.mul_(weights)
            c_tensor.mul_(weights.view(m,1,1))
            #c_tensor = c_tensor * weights
            #c_tensor = c_tensor
            if "pooled_output" in c_dict:
                pooled = c_dict['pooled_output']
                if pooled.shape[0] == 1:
                    pooled = pooled.repeat(m, 1) # batch, embeding_dim
                    #pooled.mul_(weights)
                c_dict['pooled_output'] = pooled * weights.view(m,1)
            cond_out.append((c_tensor, c_dict))
        return (cond_out,)

        #outv = torch.ones_like(latents) * torch.tensor(weights, device=latents.device)
        #return (cond, outv)


# TODO: Add Conds
#class ConditioningAverage:
class KfConditioningAdd:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"conditioning_1": ("CONDITIONING", ),
                             "conditioning_2": ("CONDITIONING", ),
                             }}
    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "main"

    CATEGORY = "conditioning"

    def main(self, conditioning_1, conditioning_2):
        assert len(conditioning_1) == len(conditioning_2)

        outv = []
        for i, ((c1_tensor, c1_dict), (c2_tensor, c2_dict) ) in enumerate(zip(conditioning_1, conditioning_2)):
            c1_tensor += c2_tensor
            if ('pooled_output' in c1_dict) and ('pooled_output' in c2_dict):
                c1_dict['pooled_output'] += c2_dict['pooled_output']
            outv.append((c1_tensor, c1_dict))
        return (outv, )

# TODO: Add Curves (to compute normalization)

# TODO: Divide Cond By Curve --> add ""

##################################################################

NODE_CLASS_MAPPINGS = {
    "KfCurveFromString": KfCurveFromString,
    "KfCurveFromYAML": KfCurveFromYAML,
    "KfEvaluateCurveAtT": KfEvaluateCurveAtT,
    "KfApplyCurveToCond": KfApplyCurveToCond,
    "KfConditioningAdd": KfConditioningAdd,
    #"KfCurveToAcnLatentKeyframe": KfCurveToAcnLatentKeyframe,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "KfCurveFromString": "Curve From String",
    "KfCurveFromYAML": "Curve From YAML",
    "KfEvaluateCurveAtT": "Evaluate Curve At T",
    "KfApplyCurveToCond": "Apply Curve to Conditioning",
    "KfConditioningAdd": "Add Conditions"
    #"KfCurveToAcnLatentKeyframe": "Curve to ACN Latent Keyframe",
}