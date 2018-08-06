# -*- coding: UTF-8 -*-
import struct
import argparse


class AnalysisPcap(object):
    """通过对pcap文件的解析

    返回TCP下的应用层数据"""

    def __init__(self, pcapath, httpfile):
        """传入两个必填参数path1 path2"""
        self.pcapath = pcapath
        self.httpfile = httpfile
        self.fpcap = open(self.pcapath, 'rb')
        self.stringData = self.fpcap.read()
        self.tcpData = open(self.httpfile, 'w+')
        self.headerLen = 24

    def pcap_file_header(self):
        """对pcap的文件包头进行解析,存入字典gather中

        返回此gather"""
        gather = dict()
        # 用来识别文件自己和字节顺序
        gather['magic_number'] = self.stringData[0:4]
        # 当前文件主要的版本号
        gather['version_major'] = self.stringData[4:6]
        # 当前文件次要的版本号
        gather['version_minor'] = self.stringData[6:8]
        # GMT和本地时间的相差，用秒来表示。
        gather['thiszone'] = self.stringData[8:12]
        # 最大的存储长度
        gather['sigfigs'] = self.stringData[12:16]
        # 每个包的最大长度
        gather['snaplen'] = self.stringData[16:20]
        # 链路类型
        gather['linktype'] = self.stringData[20:24]
        return gather

    def packet_num(self):
        """对pcap的文件包头进行解析

        返回数据包的数量"""
        pnum = 0
        while self.headerLen < len(self.stringData):
            lens = self.stringData[self.headerLen + 12:self.headerLen + 16]
            plen = struct.unpack('I', lens)[0]
            self.headerLen = self.headerLen + plen + 16
            pnum += 1
        return pnum

    def packet_ethernet_type(self, types=None):
        """获取以太网上层的type类型

        返回此type类型列表"""
        if types is None:
            types = []
        hlen = 24
        j = 0
        lens = self.packet_len()
        while hlen < len(self.stringData):
            per = hex(struct.unpack(
                '!H', self.stringData[hlen + 16 + 12:hlen + 16 + 14])[0])
            types.append(per)
            hlen = hlen + lens[j] + 16
            j += 1
        return types

    def packet_len(self, lens=None):
        """获取报头的各个数据包的长度

        返回此长度列表"""
        if lens is None:
            lens = []
        hlen = 24
        while hlen < len(self.stringData):
            packetlen = struct.unpack(
                'I', self.stringData[hlen + 12:hlen + 16])[0]
            lens.append(packetlen)
            hlen = hlen + packetlen + 16
        return lens

    def packet_ip_protocol(self, protocols=None):
        """获取以ip层的protocol类型

        返回此protocol类型列表"""
        hlen = 24
        if protocols is None:
            protocols = []
        j = 0
        lens = self.packet_len()
        types = self.packet_ethernet_type()
        while hlen < len(self.stringData):
            if types[j] == '0x800':
                per = hex(struct.unpack(
                    'b', self.stringData[hlen + 16 + 23:hlen + 16 + 24])[0])
                if per == '0x6':
                    protocols.append(per)
                else:
                    protocols.append('非TCP协议')
            else:
                protocols.append('此数据包不遵循IPV4协议')
            hlen = hlen + int(lens[j]) + 16
            j += 1
        return protocols

    def packet_ip_total_length(self, iplens=None):
        """获取每个ip数据包ip的total_length

        返回此total_length列表"""
        hlen = 24
        if iplens is None:
            iplens = []
        j = 0
        lens = self.packet_len()
        protocols = self.packet_ip_protocol()
        while hlen < len(self.stringData):
            # 判断是否为IPV4协议下的TCP协议
            if protocols[j] == '0x6':
                # 获取ip包的总长度
                iplen = int(hex(struct.unpack(
                    '!H', self.stringData[hlen + 16 + 16:hlen + 16 + 18])[0]), 16)
                iplens.append(iplen)
            else:
                iplens.append('非TCP协议')
            hlen = hlen + lens[j] + 16
            j += 1
        return iplens

    def packet_ip_ihl(self, ihls=None):
        """获取每个ip数据包ip的ihl(ip报头长度)

        返回此ihl列表"""
        hlen = 24
        if ihls is None:
            ihls = []
        j = 0
        lens = self.packet_len()
        protocols = self.packet_ip_protocol()
        while hlen < len(self.stringData):
            # 判断是否为IPV4协议下的TCP协议
            if protocols[j] == '0x6':
                # 获取ip包的总长度
                ipheader = hex(struct.unpack(
                    'b', self.stringData[hlen + 16 + 14:hlen + 16 + 15])[0])
                ipheaderlen = (int(ipheader, 16) & 0x0F) * 4
                ihls.append(ipheaderlen)
            else:
                ihls.append('非TCP协议')
            hlen = hlen + lens[j] + 16
            j += 1
        return ihls

    def packet_tcp_header_len(self, tcphs=None):
        """获取每个tcp报头长度

        返回此报头长度列表"""
        hlen = 24
        if tcphs is None:
            tcphs = []
        j = 0
        lens = self.packet_len()
        protocols = self.packet_ip_protocol()
        ihl = self.packet_ip_ihl()
        while hlen < len(self.stringData):
            # 判断是否为IPV4协议下的TCP协议
            if protocols[j] == '0x6':
                # 获取TCP包的报头长度
                tcphlen = hex(struct.unpack(
                    '!b',
                    self.stringData[hlen + 16 + 14 + ihl[j] + 12:hlen + 16 + 14 + ihl[j] + 13])[0])
                tcpheaderlen = abs(int(tcphlen, 16) >> 4) * 4
                tcphs.append(tcpheaderlen)
            else:
                tcphs.append('非TCP协议')
            hlen = hlen + lens[j] + 16
            j += 1
        return tcphs

    def packet_tcp_content(self, contents=None):
        """获取每个tcp的应用层的数据

        返回此应用层的数据列表"""
        hlen = 24
        if contents is None:
            contents = []
        j = 0
        lens = self.packet_len()
        protocols = self.packet_ip_protocol()
        ihl = self.packet_ip_ihl()
        tcphlen = self.packet_tcp_header_len()
        iplen = self.packet_ip_total_length()
        while hlen < len(self.stringData):
            # 判断是否为IPV4协议下的TCP协议
            if protocols[j] == '0x6':
                # 获取tcp下的应用层数据
                tcpcontent = self.stringData[hlen +
                                             16 +
                                             14 +
                                             ihl[j] +
                                             tcphlen[j]:hlen +
                                             16 +
                                             14 +
                                             iplen[j]]
                contents.append(tcpcontent)
            else:
                contents.append('非IPV4协议下的TCP协议')
            hlen = int(hlen) + lens[j] + 16
            j += 1
        return contents

    def packet_tcp_data(self):
        """将tcp应用层数据解析，写入本地

        返回tcp下的应用层数据文件"""
        tcpcontent = self.packet_tcp_content()
        i = 0
        num = self.packet_num()
        f = open(self.httpfile, 'w+', encoding="utf-8")
        while i < num:
            if len(tcpcontent[i]) == 0:
                f.write('TCP的应用层数据:无' + '\n')
            else:
                f.write('TCP的应用层数据:' + str(tcpcontent[i]) + '\n')
            i += 1
        f.close()
        with open(self.httpfile, 'r', encoding="utf-8") as f:
            data = f.readlines()
        return data

    def pcap_file_close(self):
        """关闭pcap文件以及txt文件"""
        self.fpcap.close()
        self.tcpData.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Process pcapfile and sava tcpdata in txt.')
    parser.add_argument('--pcap', type=str, help='pcap file path')
    parser.add_argument('--save', type=str, help='sava tcpdata file path')
    args = parser.parse_args()
    t1 = AnalysisPcap(args.pcap, args.save)
    # print(t1.pcap_file_header())
    # print(t1.packet_num())
    t1.packet_tcp_data()
    # print(t1.packet_ethernet_type())
    # print(t1.packet_ip_protocol())
    # print(t1.packet_ip_total_length())
    # print(t1.packet_ip_ihl())
    # print(t1.packet_tcp_header_len())
    # t1.packet_tcp_content()
    t1.pcap_file_close()
