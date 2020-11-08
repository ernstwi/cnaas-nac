from pyrad.client import Client
from pyrad.dictionary import Dictionary

from flask import request
from flask_restplus import Resource, Namespace, fields

from cnaas_nac.api.generic import empty_result
from cnaas_nac.tools.log import get_logger
from cnaas_nac.version import __api_version__


logger = get_logger()


api = Namespace('coa', description='Port bounce API',
                prefix='/api/{}'.format(__api_version__))

port_bounce = api.model('bounce', {
    'nas_ip_address': fields.String(required=True),
    'nas_port_id': fields.String(required=True),
    'secret': fields.String(required=True)
})


class CoA:
    def __init__(self, host, secret):
        self.client = Client(host, coaport=3799, secret=secret,
                             dict=Dictionary("dictionary"))
        self.client.timeout = 30

    def send_packet(self, attrs=None):
        try:
            self.coa_attrs = {k.replace("-", "_"): attrs[k] for k in attrs}
            self.coa_pkt = self.client.CreateCoAPacket(**self.coa_attrs)
            self.client.SendPacket(self.coa_pkt)
        except Exception as e:
            return 'Failed to send CoA packet: %s' % (str(e))

        return 'Port bounced'


class BounceApi(Resource):
    @api.expect(port_bounce)
    def post(self):
        """
        Send a CoA-Request to the NAS and tell it to flap the selected
        port.

        The VSA used to flap ports on Airsta switches is
        Arista-PortFlap and must be present in the dictionary.
        """

        json_data = request.get_json()

        if 'nas_ip_address' not in json_data:
            return empty_result(status='error', data='NAS IP address missing')
        if 'nas_port_id' not in json_data:
            return empty_result(status='error', data='NAS port ID missing')
        if 'secret' not in json_data:
            return empty_result(status='error', data='Secret required')

        logger.info(json_data)

        attrs = {
            'NAS-IP-Address': json_data['nas_ip_address'],
            'NAS-Port-Id': json_data['nas_port_id'],
            'Arista-PortFlap': '1'
        }

        secret = str.encode(json_data['secret'])
        coa_request = CoA(json_data['nas_ip_address'], secret)
        res = coa_request.send_packet(attrs=attrs)

        return empty_result(status='success', data=res)


if __name__ == '__main__':
    attrs = {
        'Tunnel-Private-Group-Id': '13',
        'Arista-PortFlap': '1'
    }

    c = CoA('localhost', b'testing123')
    print(c.send_packet(attrs=attrs))
else:
    api.add_resource(BounceApi, '')