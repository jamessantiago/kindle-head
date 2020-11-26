from pysnmp import hlapi
from statistics import mean


def construct_object_types(list_of_oids):
    object_types = []
    for oid in list_of_oids:
        object_types.append(hlapi.ObjectType(hlapi.ObjectIdentity(oid)))
    return object_types

class EsxiSnmp:
    def __init__(self, target, user, authkey, privkey, port=161):
        self.target = target
        self.port = port
        self.credentials = hlapi.UsmUserData(user, authKey=authkey, privKey=privkey, authProtocol=hlapi.usmHMACSHAAuthProtocol, privProtocol=hlapi.usmAesCfb128Protocol)

    def cast(self, value):
        try:
            return int(value)
        except (ValueError, TypeError):
            try:
                return float(value)
            except (ValueError, TypeError):
                try:
                    return str(value)
                except (ValueError, TypeError):
                    pass
        return value


    def fetch(self, handler, count):
        result = []
        for i in range(count):
            try:
                error_indication, error_status, error_index, var_binds = next(handler)
                if not error_indication and not error_status:
                    items = {}
                    for var_bind in var_binds:
                        items[str(var_bind[0])] = self.cast(var_bind[1])
                    result.append(items)
                else:
                    raise RuntimeError('Got SNMP error: {0}'.format(error_indication))
            except StopIteration:
                break
        return result


    def get(self, oids, engine=hlapi.SnmpEngine(), context=hlapi.ContextData()):
        handler = hlapi.getCmd(
            engine,
            self.credentials,
            hlapi.UdpTransportTarget((self.target, self.port)),
            context,
            *construct_object_types(oids)
        )
        return self.fetch(handler, 1)[0]

    def get_bulk(self, oids, count, start_from=0, engine=hlapi.SnmpEngine(), context=hlapi.ContextData()):
        handler = hlapi.bulkCmd(
            engine,
            self.credentials,
            hlapi.UdpTransportTarget((self.target, self.port)),
            context,
            start_from, count,
            *construct_object_types(oids),
            lexicographicMode=False
        )
        return self.fetch(handler, count)


    def get_cpu(self):
        cpu_cores = self.get_bulk([".1.3.6.1.2.1.25.3.3.1.2"], 32)
        values = []
        for core in cpu_cores:
            for key, value in core.items():
                values.append(value)
        # these values are pretty much always wrong...
        #avg = mean(values)
        minv = min(values)
        return round(minv,2)
        
    def get_mem(self):
        storage_table = self.get_bulk(["1.3.6.1.2.1.25.2.3.1.3"], 20)
        real_mem_oid = None
        for stor in storage_table:
            for key, value in stor.items():
                if value == "Real Memory":
                    real_mem_oid = "1.3.6.1.2.1.25.2.3.1.6." + key.split(".")[-1]
        if real_mem_oid == None:
            raise RuntimeException("Failed to find the real memory oid")
        real_mem = self.get([real_mem_oid])[real_mem_oid]
        total_mem = self.get(["1.3.6.1.4.1.6876.3.2.1.0"])["1.3.6.1.4.1.6876.3.2.1.0"]
        return round((float(real_mem) / float(total_mem)) * 100, 2)

    def get_nic_id(self, nic_name):
        nics = self.get_bulk(["1.3.6.1.2.1.31.1.1.1.1"], 20)
        nicid = None
        for nic in nics:
            for key, value in nic.items():
                if value == nic_name:
                    nicid = key.split(".")[-1]

        return nicid

    def get_nic_in(self, nic_name):
        nicid = self.get_nic_id(nic_name);
        in_oid = "1.3.6.1.2.1.2.2.1.10." + nicid
        inbytes = self.get([in_oid])[in_oid]
        return inbytes

    def get_nic_out(self, nic_name):
        nicid = self.get_nic_id(nic_name);
        out_oid = "1.3.6.1.2.1.2.2.1.16." + nicid
        outbytes = self.get([out_oid])[out_oid]
        return outbytes

