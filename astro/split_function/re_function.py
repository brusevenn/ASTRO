import re
import sys

from lib import config


def analyze_function(data, contract_name, address, csv_to_write):
    # data = """
    
    #     function breed() external {
    #     require(now / 1 days > today);
    #     today += 1;

    #     uint256 sealPairAmount = seal.balanceOf(address(cSeal));
    #     uint256 tokenPairAmount = token.balanceOf(address(cSeal));
    #     uint256 newSeal = sealPairAmount.mul(spawnRate).div(1e18);
    #     uint256 amount = UniswapV2Library.getAmountOut(newSeal, sealPairAmount, tokenPairAmount);

    #     seal.mint(address(cSeal), newSeal);
    #     if(address(seal) < address(token))
    #         cSeal.swap(0, amount, address(this), "");
    #     else
    #         cSeal.swap(amount, 0, address(this), "");
    #     token.transfer(address(cSeal), amount);
    #     seal.mint(address(cSeal), newSeal);
    #     cSeal.mint(address(this));
    # }
    # """
    functions = get_functions(data)
    if len(functions):
        return True
    return False

#         
def get_functions(data):
    functions = {}
    function_patterns = [config.get_function_pattern_with_return(), config.get_function_pattern_without_return()]
    for function_pattern in function_patterns:
        functions.update(_get_functions(data, function_pattern))
    return functions

def _get_functions(data, function_pattern) -> dict:
    matches = re.finditer(function_pattern, data, re.DOTALL | re.I)
    functions = {}
    for match in matches:
        #                ，            ，          ，  len( ) - len( )   0 1，   
        # function_name, function_body = match.group(1), eliminate_extra_rbrace(match.group())
        function_name, function_body = match.group(1), match.group()
        print("function name: ", function_name, "function: ", function_body)
        if function_name not in config.function_names:
            config.function_names[function_name] = 1
        else:
            config.function_names[function_name] += 1
        functions[function_name] = function_body
    return functions
    

def loop_functions(functions, contract_name, address, csv_to_write):
    pass


def count_char_occurrences(input_string, target_char):
    count = 0
    for char in input_string:
        if char == target_char:
            count += 1
    return count

def eliminate_extra_rbrace(function):
    rbrace_count = count_char_occurrences(function, "}")
    lbrace_count = count_char_occurrences(function, "{")
    if rbrace_count == lbrace_count:
        return function
    elif rbrace_count - lbrace_count:
        return find_second_to_last_brace_content(function)
    else:
        RuntimeError("           ")

def find_second_to_last_brace_content(input_string):
    brace_count = 0
    content = []

    #          
    for char in input_string:
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count < 0:
                #                   
                return ''.join(content)
        content.append(char)

    #                ，               
    raise RuntimeError("             ")


if __name__ == "__main__":
        data = """
    
        function breed() external {
        require(now / 1 days > today);
        today += 1;

        uint256 sealPairAmount = seal.balanceOf(address(cSeal));
        uint256 tokenPairAmount = token.balanceOf(address(cSeal));
        uint256 newSeal = sealPairAmount.mul(spawnRate).div(1e18);
        uint256 amount = UniswapV2Library.getAmountOut(newSeal, sealPairAmount, tokenPairAmount);

        seal.mint(address(cSeal), newSeal);
        if(address(seal) < address(token))
            cSeal.swap(0, amount, address(this), "");
        else
            cSeal.swap(amount, 0, address(this), "");
        token.transfer(address(cSeal), amount);
        seal.mint(address(cSeal), newSeal);
        cSeal.mint(address(this));
    }
    """