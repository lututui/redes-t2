import asyncio
import random

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
            conexao = self.conexoes[id_conexao] = Conexao(self, id_conexao, random.randint(0, 0xffff), seq_no + 1)

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

        self.servidor.rede.enviar(self._mk_header(seq_no, ack_no, b'', FLAGS_SYN | FLAGS_ACK), self.id_conexao[0])

    def _rdt_rcv(self, seq_no, ack_no, flags, payload):
        # print('recebido payload: %r' % payload)

        if seq_no == self.ack_no and payload:
            self.ack_no += len(payload)

            self.callback(self, payload)

            seg = make_header(self.id_conexao[3], self.id_conexao[1], self.seq_no, self.ack_no, FLAGS_ACK)
            self.servidor.rede.enviar(fix_checksum(seg, self.id_conexao[0], self.id_conexao[2]), self.id_conexao[0])

    # Os métodos abaixo fazem parte da API

    def registrar_recebedor(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que dados forem corretamente recebidos
        """
        self.callback = callback

    def _mk_header(self, seq_no, ack_no, dados, flags):
        return fix_checksum(
            make_header(self.id_conexao[3], self.id_conexao[1], seq_no, ack_no, flags) + dados,
            self.id_conexao[2],
            self.id_conexao[0]
        )

    def enviar(self, dados):
        """
        Usado pela camada de aplicação para enviar dados
        """

        for i in range(int(len(dados) / MSS)):
            self.seq_no += MSS

            self.servidor.rede.enviar(
                self._mk_header(self.seq_no - MSS + 1, self.ack_no, dados[i * MSS:(i + 1) * MSS], FLAGS_ACK),
                self.id_conexao[0]
            )

    def fechar(self):
        """
        Usado pela camada de aplicação para fechar a conexão
        """
        # TODO: implemente aqui o fechamento de conexão
        pass
