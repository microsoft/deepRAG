def agent_run(client,engine,function_spec,functions_list):
        prompt =""
        conversation = ({"role": "user", "content": prompt})
        while True:
            response = client.chat.completions.create(
                model=engine, 
                messages=conversation,
                tools=function_spec,
                tool_choice='auto',
                
            )
            
            response_message = response.choices[0].message
            if response_message.content is None:
                response_message.content = ""
            tool_calls = response_message.tool_calls
            

            # Step 2: check if GPT wanted to call a function
            if  tool_calls:
                conversation.append(response_message)  # extend conversation with assistant's reply
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    print("Recommended Function call:")
                    print(function_name)
                    print()                                    
                    # verify function exists
                    if function_name not in functions_list:
                        # raise Exception("Function " + function_name + " does not exist")
                        conversation.pop()
                        continue
                    function_to_call = functions_list[function_name]
                    
                    # verify function has correct number of arguments
                    function_args = json.loads(tool_call.function.arguments)

                    # print("beginning function call")
                    function_response = str(function_to_call(**function_args))

                    print("Output of function call:")
                    print(function_response)
                    print()
                
                    conversation.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        }
                    )  # extend conversation with function response
            else:
                break #if no function call break out of loop as this indicates that the agent finished the research and is ready to respond to the user

        return response_message.content.strip() #return the response to the user