def parameters(argv):
    commands = list()
    flags = set()
    params = dict()

    param = None
    for arg in argv:
        if arg is not None:
            if param is not None:
                params[param] = arg
                param = None
            elif arg.startswith('--'):
                param = arg[2:]
            elif arg.startswith('-'):
                flags.add(arg[1:])
            else:
                commands.append(arg)
    return {
        'commands': commands,
        'flags': flags,
        'params': params
    }


class Command:
    def __init__(self, name=None, comment=None):
        self.name = name
        self.comment = comment
        self.actions = list()
        self.flags = list()
        self.params = list()
        self.next_command = dict()
        self.throws = dict()
        self.do_delegate = None

    def a(self, name, display_name=None, required=False, clazz=None, default=None, comment=None):
        if required:
            for action in self.actions:
                if not action['required']:
                    raise Exception('required action must be front of not required.')
        self.actions.append({
            'name': name,
            'display_name': display_name or name.upper(),
            'required': required,
            'clazz': clazz,
            'default': default,
            'comment': comment
        })
        return self

    def f(self, name, display_list=None, comment=None):
        dl = [name] if display_list is None else [display_list] if isinstance(display_list, str) else display_list
        self.flags.append({
            'name': name,
            'display_list': dl,
            'comment': comment
        })
        return self

    def p(self, name, display_list=None, display_name=None, required=False, clazz=None, default=None, comment=None):
        dl = [name] if display_list is None else [display_list] if isinstance(display_list, str) else display_list
        self.params.append({
            'name': name,
            'display_name': display_name or name.upper(),
            'display_list': dl,
            'required': required,
            'clazz': clazz,
            'default': default,
            'comment': comment
        })
        return self

    def next(self, *command):
        for c in command:
            if c.name in self.next_command:
                raise Exception('duplicate command %s' % (c.name,))
            self.next_command[c.name] = c
        return self

    def throw(self, **kwargs):
        for k, v in kwargs.items():
            if not callable(v):
                raise Exception('throw must be callable.')
            self.throws[k] = v
        for next_command in self.next_command.values():
            next_command.throw(**kwargs)
        return self

    def do(self, delegate):
        self.do_delegate = delegate
        return self

    def execute(self, commands, flags, params, history=None):
        if len(self.next_command) > 0 and len(commands) > 0:
            next_command = commands[0]
            if next_command in self.next_command:
                next_history = ([] if history is None else history) + ([] if self.name is None else [self.name])
                if not self.next_command[next_command].execute(commands[1:], flags, params, next_history):
                    return False
            elif 'no_next_command' in self.throws:
                self.throws['no_next_command'](commands, flags, params)
                return False
            else:
                default_no_next_command(commands, flags, params)
                return False
        elif len(commands) == 0 and 'h' in flags:
            if 'help' in self.throws:
                self.throws['help'](self, history)
            else:
                default_help(self, history)
        elif self.do_delegate is not None and callable(self.do_delegate):
            actions = self.__generate_actions(commands)
            flags = self.__generate_flags(flags)
            params = self.__generate_params(params)
            if actions is None or flags is None or params is None:
                return False
            self.do_delegate(actions, flags, params)
        return True

    def __generate_actions(self, commands):
        ret = dict()
        for index, action in enumerate(self.actions):
            if index < len(commands):
                value, error = Command.__analyse_type(action['clazz'], commands[index])
                if error is not None:
                    if 'validate_failed' in self.throws:
                        self.throws['validate_failed'](action['display_name'], error, value, commands[index])
                    else:
                        default_validate_failed(action['display_name'], error, value, commands[index])
                    return None
                ret[action['name']] = value
            elif action['required']:
                if 'required_not_exist' in self.throws:
                    self.throws['required_not_exist'](action['display_name'])
                else:
                    default_required_not_exist(action['display_name'])
                return None
            elif action['default'] is not None:
                ret[action['name']] = action['default']
        return ret

    def __generate_flags(self, flags):
        ret = dict()
        for flag in self.flags:
            for d in flag['display_list']:
                if d in flags:
                    ret[flag['name']] = True
                    break
            else:
                ret[flag['name']] = False
        return ret

    def __generate_params(self, params):
        ret = dict()
        for param in self.params:
            for d in param['display_list']:
                if d in params:
                    origin_value = params[d]
                    value, error = Command.__analyse_type(param['clazz'], origin_value)
                    if error is not None:
                        if 'validate_failed' in self.throws:
                            self.throws['validate_failed'](param['display_name'], error, value, origin_value)
                        else:
                            default_validate_failed(param['display_name'], error, value, origin_value)
                        return None
                    ret[param['name']] = value
                    break
            else:
                if param['required']:
                    if 'required_not_exist' in self.throws:
                        self.throws['required_not_exist'](param['display_name'])
                    else:
                        default_required_not_exist(param['display_name'])
                elif param['default'] is not None:
                    ret[param['name']] = param['default']
        return ret

    @staticmethod
    def __analyse_type(clazz, value):
        if clazz is None:
            return value, None
        elif clazz == str:
            return str(value), None
        elif clazz == int:
            try:
                return int(value), None
            except ValueError:
                return None, '\'%s\' cannot convert to int' % (value,)
        elif clazz == float:
            try:
                return float(value), None
            except ValueError:
                return None, '\'%s\' cannot convert to float' % (value,)
        elif isinstance(clazz, list):
            if value in clazz:
                return value, None
            else:
                return None, 'value must be %s' % (clazz,)
        elif isinstance(clazz, tuple):
            if len(clazz) == 2:
                list_type, element_type = clazz
                delimiter = ','
            elif len(clazz) == 3:
                list_type, element_type, delimiter = clazz
            else:
                raise Exception('nested type only support 2 nested (A, B) or 3 nested(A, B, \',\')')
            arr = [i.strip() for i in value.split(delimiter)]
            values = []
            for i in arr:
                value, error = Command.__analyse_type(element_type, i)
                if error is not None:
                    return None, error
                values.append(value)
            return list_type(values), None
        elif callable(clazz):
            v = clazz(value)
            if v is not None:
                return v, None
            else:
                return None, '\'%s\' validate failed' % (value,)
        else:
            raise Exception('unknown class type \'%s\'' % (clazz,))


def default_no_next_command(commands, flags, params):
    print('no next command named \'%s\'.' % (commands[0]))


def default_validate_failed(display_name, error, value, origin_value):
    print('[%s] has wrong value: %s.' % (display_name, error))


def default_required_not_exist(display_name):
    print('[%s] is required.' % (display_name,))


def default_help(command, history=None):
    actions = ([] if history is None else history) + ([command.name] if command.name is not None else [])
    print('%s%s%s%s%s' % (''.join(a + ' ' for a in actions),
                          '[ACTIONS] ' if len(command.next_command) > 0 or len(command.actions) > 0 else '',
                          '[ARGS] ' if len(command.flags) > 0 or len(command.params) > 0 else '',
                          ': ' if len(actions) > 0 and command.comment is not None else '',
                          command.comment or ''))
    if len(command.next_command) > 0:
        max_len = max(len(next_command.name) for next_command in command.next_command.values())
        template = ' %%-%ds%%s%%s' % (max_len,)
        for next_command in command.next_command.values():
            print(template % (next_command.name,
                              ' : ' if next_command.comment is not None else '',
                              next_command.comment or ''))
    else:
        line = []
        for action in command.actions:
            line.append(('[%s]' % (action['display_name'],), action['comment']))
        for flag in command.flags:
            line.append(('|'.join('-' + i for i in flag['display_list']), flag['comment']))
        for param in command.params:
            line.append(('%s [%s]' % ('|'.join('--' + i for i in param['display_list']),
                                      param['display_name']), param['comment']))
        max_len = max(len(i) for i, j in line)
        template = ' %%-%ds%%s%%s' % (max_len,)
        for i, j in line:
            print(template % (i, ' : ' if j is not None else '', j or ''))
