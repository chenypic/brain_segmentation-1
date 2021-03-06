import chainer
import chainer.functions as F
import chainer.links as L


class VoxResModule(chainer.Chain):
    """
    Voxel Residual Module
    input
    BatchNormalization, ReLU
    Conv 64, 3x3x3
    BatchNormalization, ReLU
    Conv 64, 3x3x3
    output
    """

    def __init__(self):
        init = chainer.initializers.HeNormal(scale=0.01)
        super(VoxResModule, self).__init__(
            bnorm1=L.BatchNormalization(size=64),
            conv1=L.ConvolutionND(3, 64, 64, 3, pad=1, initialW=init),
            bnorm2=L.BatchNormalization(size=64),
            conv2=L.ConvolutionND(3, 64, 64, 3, pad=1, initialW=init))

    def __call__(self, x, train):
        h = F.relu(self.bnorm1(x, test=not train))
        h = self.conv1(h)
        h = F.relu(self.bnorm2(h, test=not train))
        h = self.conv2(h)
        return h + x


class VoxResNet(chainer.Chain):
    """Voxel Residual Network"""

    def __init__(self, in_channels=1, n_classes=4):
        init = chainer.initializers.HeNormal(scale=0.01)
        super(VoxResNet, self).__init__(
            conv1a=L.ConvolutionND(3, in_channels, 32, 3, pad=1, initialW=init),
            bnorm1a=L.BatchNormalization(32),
            conv1b=L.ConvolutionND(3, 32, 32, 3, pad=1, initialW=init),
            bnorm1b=L.BatchNormalization(32),
            conv1c=L.ConvolutionND(3, 32, 64, 3, stride=2, pad=1, initialW=init),
            voxres2=VoxResModule(),
            voxres3=VoxResModule(),
            bnorm3=L.BatchNormalization(64),
            conv4=L.ConvolutionND(3, 64, 64, 3, stride=2, pad=1, initialW=init),
            voxres5=VoxResModule(),
            voxres6=VoxResModule(),
            bnorm6=L.BatchNormalization(64),
            conv7=L.ConvolutionND(3, 64, 64, 3, stride=2, pad=1, initialW=init),
            voxres8=VoxResModule(),
            voxres9=VoxResModule(),
            c1deconv=L.DeconvolutionND(3, 32, 32, 3, pad=1, initialW=init),
            c1conv=L.ConvolutionND(3, 32, n_classes, 3, pad=1, initialW=init),
            c2deconv=L.DeconvolutionND(3, 64, 64, 4, stride=2, pad=1, initialW=init),
            c2conv=L.ConvolutionND(3, 64, n_classes, 3, pad=1, initialW=init),
            c3deconv=L.DeconvolutionND(3, 64, 64, 6, stride=4, pad=1, initialW=init),
            c3conv=L.ConvolutionND(3, 64, n_classes, 3, pad=1, initialW=init),
            c4deconv=L.DeconvolutionND(3, 64, 64, 10, stride=8, pad=1, initialW=init),
            c4conv=L.ConvolutionND(3, 64, n_classes, 3, pad=1, initialW=init)
        )

    def __call__(self, x, train=False):
        """
        calculate output of VoxResNet given input x

        Parameters
        ----------
        x : (batch_size, in_channels, xlen, ylen, zlen) ndarray
            image to perform semantic segmentation

        Returns
        -------
        proba: (batch_size, n_classes, xlen, ylen, zlen) ndarray
            probability of each voxel belonging each class
            elif train=True, returns tuple of logits
        """
        h = self.conv1a(x)
        h = F.relu(self.bnorm1a(h, test=not train))
        h = self.conv1b(h)
        c1 = F.clipped_relu(self.c1deconv(h))
        c1 = self.c1conv(c1)

        h = F.relu(self.bnorm1b(h, test=not train))
        h = self.conv1c(h)
        h = self.voxres2(h, train)
        h = self.voxres3(h, train)
        c2 = F.clipped_relu(self.c2deconv(h))
        c2 = self.c2conv(c2)

        h = F.relu(self.bnorm3(h, test=not train))
        h = self.conv4(h)
        h = self.voxres5(h, train)
        h = self.voxres6(h, train)
        c3 = F.clipped_relu(self.c3deconv(h))
        c3 = self.c3conv(c3)

        h = F.relu(self.bnorm6(h, test=not train))
        h = self.conv7(h)
        h = self.voxres8(h, train)
        h = self.voxres9(h, train)
        c4 = F.clipped_relu(self.c4deconv(h))
        c4 = self.c4conv(c4)

        c = c1 + c2 + c3 + c4
        if train:
            return (c1, c2, c3, c4, c)
        else:
            return F.softmax(c)
