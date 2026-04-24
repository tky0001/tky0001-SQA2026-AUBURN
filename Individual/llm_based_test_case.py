import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import time
import argparse
from huggingface_hub import login

login(token="[HIDDEN FOR GITHUB]")

class LLMTestCaseGenerator:
    def __init__(self, model_name="mistralai/Mistral-7B-Instruct-v0.2"):
        self.model_name = model_name
        
    def load_fp16_model(self):
        start_time = time.time()
    
        self.fp16_tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.fp16_model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16,
            device_map="cpu"
        )
    
        load_time = time.time() - start_time
        print(f"FP16 loaded on CPU in {load_time:.2f}s")
        return load_time, 0
    
    def load_quantized_model(self):
        start_time = time.time()
    
        # Don't use quantization config - load directly on CPU
        self.quantized_tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.quantized_model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16,
            device_map="cpu",  # Force CPU instead of GPU
            low_cpu_mem_usage=True  
        )
    
        load_time = time.time() - start_time
        print(f"Quantized model loaded on CPU in {load_time:.2f}s")
        return load_time, 0  
    
    def generate_test_case(self, model, tokenizer, requirement, test_case_id):
        prompt = f"""Generate a test case for this regulatory requirement:

Requirement: {requirement['requirement_id']} - {requirement['description']}

Example test case format:
{{
  "test_case_id": "TC-001",
  "requirement_id": "REQ-117.130-001A", 
  "description": "Verify hazard analysis is conducted",
  "input_data": "Food facility producing canned tuna",
  "expected_output": "Written hazard analysis document",
  "steps": ["Review facility records", "Check for hazard analysis"],
  "notes": "Analysis must identify biological/chemical/physical hazards"
}}

Now generate a test case for {requirement['requirement_id']}. Output ONLY valid JSON:"""

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        start_time = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,      # Reduced from 300 (much faster)
                do_sample=False,        # Deterministic = faster
                num_beams=1,           # No beam search
                pad_token_id=tokenizer.eos_token_id
            )
        inference_time = time.time() - start_time
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract JSON from response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            test_case = json.loads(response[json_start:json_end])
            test_case['inference_time'] = inference_time
            return test_case
        
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements", "-r", required=True, help="Path to requirements.json")
    parser.add_argument("--output", "-o", default="test_cases.json")
    args = parser.parse_args()
    
    # Loading Requirements from Task 1
    with open(args.requirements, 'r', encoding='utf-8') as f:
        all_requirements = json.load(f)
    
    # Atomic Rules from Task 1
    selected_rules = [
        {"id": "REQ-117.130-001A", "desc": "Conduct hazard analysis"},
        {"id": "REQ-117.130-001B", "desc": "Identify known hazards"},
        {"id": "REQ-117.130-002A", "desc": "Biological hazards"},
        {"id": "REQ-117.130-003A1", "desc": "Assess severity and probability"},
        {"id": "REQ-117.130-003B1", "desc": "Formulation of the food"}
    ]
    
    # Load requirement object
    requirements = []
    for rule in selected_rules:
        req = next((r for r in all_requirements if r['requirement_id'] == rule['id']), None)
        if req:
            requirements.append(req)
    
    print(f"Selected {len(requirements)} atomic rules:")
    for req in requirements:
        print(f"  - {req['requirement_id']}: {req['description']}")
    
    # Initialize generator
    generator = LLMTestCaseGenerator()
    
    # Load models
    fp16_time, fp16_memory = generator.load_fp16_model()
    quantized_time, quantized_memory = generator.load_quantized_model()
    
    # Generate test cases
    results = {
        "fp16": [],
        "quantized": []
    }
    
    # Generating the FP16 test cases
    for i, req in enumerate(requirements, 1):
        test_case_id = f"TC-FP16-{i:03d}"
        test_case = generator.generate_test_case(
            generator.fp16_model, 
            generator.fp16_tokenizer, 
            req, 
            test_case_id
        )
        if test_case:
            results["fp16"].append(test_case)
            print(f"Generated {test_case_id} for {req['requirement_id']}")
    
    # Generating the quantized test cases
    for i, req in enumerate(requirements, 1):
        test_case_id = f"TC-QT-{i:03d}"
        test_case = generator.generate_test_case(
            generator.quantized_model, 
            generator.quantized_tokenizer, 
            req, 
            test_case_id
        )
        if test_case:
            results["quantized"].append(test_case)
            print(f"Generated {test_case_id} for {req['requirement_id']}")
    
    # Save results
    output = {
        "metadata": {
            "model": generator.model_name,
            "fp16_load_time_seconds": fp16_time,
            "fp16_memory_gb": fp16_memory,
            "quantized_load_time_seconds": quantized_time,
            "quantized_memory_gb": quantized_memory
        },
        "test_cases": results
    }
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nSaved {len(results['fp16'])} FP16 + {len(results['quantized'])} quantized test cases to {args.output}")

if __name__ == "__main__":
    main()