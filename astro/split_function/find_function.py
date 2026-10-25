import os
import re
import sys

from lib.timeout_decorator import timeout
from split_function.function_name_check import check_similar_function

def find_func(data, start, end):
    stack = []; flag = 0; res = ""
    for i in data[start:end]:
        if(flag == 1 and len(stack) == 0):
            break
        if(i == "{"):
            stack.append(i)
            flag = 1
        if(i == "}"):
            if(len(stack) == 0):
                return ""
            stack.pop(-1)
        res += i
    if(flag == 0):
        return ""
    return res

def get_functions(data):
    pos = []
    pos.append(data.find("function "))
    while(pos[-1] != -1):
        pos.append(data.find("function ", pos[-1] + 1))

    # print(pos)

    functions = []
    for i in range(1, len(pos)):
        start = pos[i - 1]
        end = pos[i]
        if(pos[i] == -1):
            end = len(data) - 1
        function = find_func(data, start, end)
        if(function != ""):
            functions.append(function)
    return functions


def loop_functions(functions, contract_name, address, csv_to_write):
    functions_length = len(functions)
    similar_function_exist = False
    for i in range(functions_length):
        for j in range(i + 1, functions_length):
            if check_similar_function(functions[i], functions[j], contract_name, address, csv_to_write):
                similar_function_exist = True
    return similar_function_exist

def analyze_function(data, contract_name, address, csv_to_write):
    functions = []
    functions = get_functions(data)
    # for function in functions:
    #     print("function: ", function)
    if loop_functions(functions, contract_name, address, csv_to_write):
        print("the address need to analyze")
        return True
    return False

@timeout(30)
def remove_comments(code):
    
    #        /** ... */
    code = re.sub(r"/\*(.|[\r\n])*?\*/", "", code)
    
    #        /* ... */
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    
    #        //
    code = re.sub(r"//.*", "", code)
    
    return code


if __name__ == "__main__":
    data = '''
contract Lottery {
    // user address -> lottery id -> count
    mapping (address => mapping(uint64 => uint)) public tickets;
    uint64 winningId; // the winning id
    bool drawingPhase; // whether the owner is drawing

    // invoked every day to reset a round
    function reset() external onlyOwner {
        delete tickets;
        winningId = 0;
        drawingPhase = false;
    }

    function buy(uint64 id, uint amount) external {
        require(winningId == 0, "already drawn");
        require(!drawingPhase, "drawing");
        receivePayment(msg.sender, amount);
        tickets[msg.sender][id] += amount;
    }

    function enterDrawingPhase() external onlyOwner {
        drawingPhase = true;
    }

    // id is randomly chosen off-chain, i.e., by chainlink
    function draw(uint64 id) external onlyOwner {
        require(winningId == 0, "already drawn");
        require(drawingPhase, "not drawing");
        require(id != 0, "invalid winning number");
        winningId = id;
    }

    // claim reward for winners
    function claimReward() external {
        require(winningId != 0, "not drawn");
        ...
    }

    function multiBuy(uint64[] ids, uint[] amounts) external {
        require(winningId == 0, "already drawn");
        uint totalAmount = 0;
        for (int i = 0; i < ids.length; i++) {
            tickets[msg.sender][ids[i]] += amounts[i];
            totalAmount += amounts[i];
        }
        receivePayment(msg.sender, totalAmount);
    }
}
'''
    analyze_function(data, "test", "0x00", "file")
