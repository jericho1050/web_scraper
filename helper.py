import json

def get_actor_config(config_path):
    """
    Load configuration from JSON and
    returns JSON actor config
    """
    # Load configuration
    with open(config_path) as f:
        config = json.load(f)
        config["actor_input"]["cookie"] = get_input_cookie("input.JSON")
    
    return config
    
def get_input_cookie(filename):
    """
    Load configuration from JSON and
    returns JSON cookie 
    """
    with open(filename) as f:
        actor_input = json.load(f)
        
    return actor_input["cookie"]    

if __name__ == "__main__":
    pass
    