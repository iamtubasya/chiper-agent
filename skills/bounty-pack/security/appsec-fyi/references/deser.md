## Notable Techniques

Notable Techniques
Attackers leverage various techniques to exploit deserialization vulnerabilities. These often revolve around identifying and chaining together existing code fragments (gadgets) within the application's libraries or the runtime environment to achieve a malicious outcome.

Gadget Chains
A deserialization gadget chain is a sequence of method invocations on existing, legitimate objects that, when triggered during deserialization, lead to arbitrary code execution or other harmful actions . The core idea is to manipulate the deserialized object graph such that specific methods are called in a sequence that results in the desired malicious outcome.

• Java: ysoserial is a well-known tool that provides numerous gadget chains for common Java libraries like Apache Commons Collections, Spring, and Hibernate . The CommonsCollections1 chain, for instance, uses LazyMap and ChainedTransformer to achieve RCE .

• .NET: ysoserial.net offers similar functionality for .NET, targeting formatters like BinaryFormatter and Json.NET with gadgets such as ObjectDataProvider or ActivitySurrogateSelector .

• Python: Gadgets can be chained using Python's pickle or other libraries. The __reduce__ method is a common entry point .

• PHP: Property-Oriented Programming (POP) chains are utilized, often involving magic methods like __destruct() and __wakeup() to chain method calls and achieve RCE .

• Ruby: Gadgets are sourced from the standard library and other gem dependencies, often leading to Marshal.load exploitation .

Specific Exploitation Vectors

• Type Confusion: In some serialization libraries, the type of data being deserialized is not properly validated. For example, seroval deserialized typed-array and data-view nodes without checking the expected buffer type, allowing numbers or arrays to be substituted for ArrayBuffers, leading to DoS or function invocation .

• .NET ViewState Deserialization: ASP.NET's ViewState mechanism, if not properly protected with a strong machine key, can be exploited by crafting malicious serialized objects within the __VIEWSTATE parameter, leading to RCE .

• PHAR Deserialization (PHP): The phar:// stream wrapper can deserialize metadata from PHAR archives. By controlling the metadata (e.g., via setMetadata()), an attacker can inject malicious objects, often leveraging magic methods in the destructor (__destruct()) to achieve RCE .

• JSON Deserialization: While JSON is generally considered safer than binary formats due to its data-centric nature, vulnerabilities can still arise if JSON parsers are configured to handle polymorphic types or if they interact with other unsafe deserialization mechanisms . For instance, Wazuh's custom object_hook for JSON deserialization allowed arbitrary module imports and function execution .

• YAML Deserialization: Libraries like PyYAML and SnakeYAML can be vulnerable if configured to use unsafe loading functions, allowing arbitrary object instantiation during parsing .

• Language-Specific Sinks: Many languages have specific functions or methods that act as sinks for deserialization vulnerabilities, such as pickle.loads() in Python , unserialize() in PHP , Marshal.load() in Ruby , ObjectInputStream.readObject() in Java , and various .NET formatters .