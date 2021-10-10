import asyncio
from random import randint

from tcputils import *


class Servidor:
    def __init__(self, rede, porta):
        self.rede = rede
        self.porta = porta
        self.conexoes = {}
        self.callback = None
        self.rede.registrar_recebedor(self._rdt_rcv)

    def registrar_monitor_de_conexoes_aceitas(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que uma nova conexão for aceita
        """
        self.callback = callback

    def _rdt_rcv(self, src_addr, dst_addr, segment):
        src_port, dst_port, seq_no, ack_no, flags, window_size, checksum, urg_ptr = read_header(segment)

        if dst_port != self.porta:
            # Ignora segmentos que não são destinados à porta do nosso servidor
            return
        if not self.rede.ignore_checksum and calc_checksum(segment, src_addr, dst_addr) != 0:
            print('descartando segmento com checksum incorreto')
            return

        payload = segment[4 * (flags >> 12):]
        id_conexao = (src_addr, src_port, dst_addr, dst_port)

        if (flags & FLAGS_SYN) == FLAGS_SYN:
            # A flag SYN estar setada significa que é um cliente tentando estabelecer uma conexão nova

            server_seq_no = randint(0, 0xffff)
            server_ack_no = seq_no + 1

            conexao = self.conexoes[id_conexao] = Conexao(self, id_conexao, server_seq_no, server_ack_no)

            if self.callback:
                self.callback(conexao)
        elif id_conexao in self.conexoes:
            # Passa para a conexão adequada se ela já estiver estabelecida
            self.conexoes[id_conexao]._rdt_rcv(seq_no, ack_no, flags, payload)
        else:
            print('%s:%d -> %s:%d (pacote associado a conexão desconhecida)' %
                  (src_addr, src_port, dst_addr, dst_port))


class Conexao:
    def __init__(self, servidor, id_conexao, seq_no, ack_no):
        self.servidor = servidor
        self.id_conexao = id_conexao
        self.callback = None
        self.seq_no = seq_no
        self.ack_no = ack_no

        handshake_header = make_header(
            self.id_conexao[3],
            self.id_conexao[1],
            self.seq_no,
            self.ack_no,
            FLAGS_SYN | FLAGS_ACK
        )
        self.servidor.rede.enviar(
            fix_checksum(handshake_header, self.id_conexao[2], self.id_conexao[0]),
            self.id_conexao[0]
        )
        self.seq_no += 1

        self.servidor.callback(self)

        # um timer pode ser criado assim; esta linha é só um exemplo e pode ser removida
        # self.timer = asyncio.get_event_loop().call_later(1, self._exemplo_timer)

        # é possível cancelar o timer chamando esse método; esta linha é só um exemplo e pode ser removida
        # self.timer.cancel()

    def _exemplo_timer(self):
        # Esta função é só um exemplo e pode ser removida
        print('Este é um exemplo de como fazer um timer')

    def _rdt_rcv(self, seq_no, ack_no, flags, payload):
        print(f'expected ack: {self.ack_no}, got seq: {seq_no}')
        if self.ack_no == seq_no:
            print("RECEIVED CORRECT")
            self.callback(self.id_conexao, payload)
            self.ack_no += len(payload)

            segmento = fix_checksum(
                make_header(
                    self.id_conexao[3],
                    self.id_conexao[1],
                    ack_no,
                    self.ack_no,
                    FLAGS_ACK
                ),
                self.id_conexao[2],
                self.id_conexao[0]
            )

            self.servidor.rede.enviar(segmento, self.id_conexao[0])

            print(f'recebido payload len: {len(payload)}, seq_no: {seq_no}, ack_no: {ack_no}')
            print('%r' % payload)


    # Os métodos abaixo fazem parte da API

    def registrar_recebedor(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que dados forem corretamente recebidos
        """
        self.callback = callback

    def enviar(self, dados):
        """
        Usado pela camada de aplicação para enviar dados
        """
        pass

    def fechar(self):
        """
        Usado pela camada de aplicação para fechar a conexão
        """
        # TODO: implemente aqui o fechamento de conexão
        pass
