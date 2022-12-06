import torch


class __default_graph(torch.nn.Module):
    DEFAULT_TENSOR_PREFIX = ''
    DEFAULT_TENSOR_SUFFIX = 0
    DEFAULT_DEVICE = 'cuda'
    PREFIX_SPLIT = '/'
    SUFFIX_SPLIT = ':'
    def __init__(self):
        super().__init__()
        if not torch.cuda.is_available():
            self.DEFAULT_DEVICE = 'cpu'
        self.module_cache = torch.nn.ModuleDict()
        self.param_cache = {}
        self._tensor_prefix = ''
        self._current_device = self.DEFAULT_DEVICE
    
    def get_device(self):
        return self._current_device
    
    def set_device(self, device):
        device_map = {'/cpu:0': 'cpu', 'cpu':'cpu', 'cuda': 'cuda'}
        device_map.update({'/gpu:%i'%i: 'cuda:%i'%i for i in range(1,100)})
        self._current_device = device_map[device]

    def add_param(self, name, param):
        full_name_no_suffix = f'{self._tensor_prefix}{self.PREFIX_SPLIT}{name}'
        suffix = 0
        full_name = f"{full_name_no_suffix}{self.SUFFIX_SPLIT}{suffix}"
        while full_name in self.param_cache:
            suffix += 1
            full_name = f"{full_name_no_suffix}{self.SUFFIX_SPLIT}{suffix}"
        self.param_cache[full_name] = param
        setattr(self, full_name, param)
    
    def append_var_scope(self, varscope):
        self._tensor_prefix += f'{self.PREFIX_SPLIT}{varscope}'

    def strip_var_scope(self):
        new_scopes = self._tensor_prefix.split(self.PREFIX_SPLIT)
        self._tensor_prefix = self.PREFIX_SPLIT.join(new_scopes[:-1])


GLOBAL_DEFAULT_GRAPH = __default_graph()
